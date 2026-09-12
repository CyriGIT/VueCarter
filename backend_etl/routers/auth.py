from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session
import jwt
from backend_etl.database.session import get_db
from backend_etl.schemas.auth import AcceptInvitationSchema, RegisterSchema, LoginSchema, TokenResponse
from backend_etl.core.config import settings
from backend_etl.core.security import create_access_token, get_password_hash, verify_password

router = APIRouter(prefix="/auth", tags=["Authentification"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(data: RegisterSchema, db: Session = Depends(get_db)):
    existing_account = db.execute(
        text('SELECT 1 FROM "CompteUtilisateur" WHERE lower(email) = lower(:email)'),
        {"email": data.email},
    ).first()
    if existing_account:
        raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée.")

    hashed_pwd = get_password_hash(data.password)

    person = db.execute(
        text('''
            INSERT INTO "Personne" (
                nom_civil, prenom, date_naissance, genre, npa, ville, email
            ) VALUES (
                :nom, :prenom, COALESCE(:date_naissance, CURRENT_DATE), :genre,
                '0000', :commune, :email
            )
            RETURNING id_personne
        '''),
        {
            "nom": data.nom,
            "prenom": data.prenom,
            "date_naissance": data.date_naissance,
            "genre": data.genre,
            "commune": data.commune,
            "email": data.email,
        },
    ).one()

    account = db.execute(
        text('''
            INSERT INTO "CompteUtilisateur" (
                email, nom_affichage, mot_de_passe_hash, id_role, id_personne
            ) VALUES (:email, :display_name, :password_hash, 4, :id_personne)
            RETURNING id_utilisateur
        '''),
        {
            "email": data.email,
            "display_name": f"{data.prenom} {data.nom}".strip(),
            "password_hash": hashed_pwd,
            "id_personne": person.id_personne,
        },
    ).one()

    db.commit()
    token = create_access_token({
        "sub": str(account.id_utilisateur),
        "role": "artiste",
        "id_personne": person.id_personne,
    })
    return {"access_token": token, "token_type": "bearer", "role": "artiste"}


@router.post("/login", response_model=TokenResponse)
def login(data: LoginSchema, db: Session = Depends(get_db)):
    account = db.execute(
        text('''
                 SELECT c.id_utilisateur, c.mot_de_passe_hash, c.est_actif,
                     c.id_personne,
                   c.id_role, r.libelle_role
            FROM "CompteUtilisateur" c
            JOIN "RoleUtilisateur" r ON r.id_role = c.id_role
            WHERE lower(c.email) = lower(:email)
        '''),
        {"email": data.email},
    ).mappings().first()

    if not account or not account["est_actif"] or not verify_password(
        data.password, account["mot_de_passe_hash"]
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse e-mail ou mot de passe incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_by_id = {
        1: "admin",
        2: "gestionnaire_case",
        3: "expert_jury",
        4: "artiste",
        5: "accompagnant",
    }
    role = role_by_id.get(account["id_role"])
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Rôle utilisateur non pris en charge.")
    token = create_access_token({
        "sub": str(account["id_utilisateur"]),
        "role": role,
        "id_personne": account["id_personne"],
    })
    return {"access_token": token, "token_type": "bearer", "role": role}


@router.post("/accept-invitation", response_model=TokenResponse)
def accept_invitation(data: AcceptInvitationSchema, db: Session = Depends(get_db)):
    """Finalise une invitation de membre : crée le CompteUtilisateur pour une Personne déjà existante."""
    try:
        payload = jwt.decode(data.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Lien d'invitation invalide ou expiré.",
        ) from error

    if payload.get("type") != "account_creation":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Lien d'invitation invalide.")

    email = payload.get("sub")
    role = payload.get("role", "artiste")

    role_id_by_name = {"gestionnaire_case": 2, "expert_jury": 3, "artiste": 4, "accompagnant": 5}
    if role not in role_id_by_name:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Rôle d'invitation invalide.")

    person = db.execute(
        text('SELECT id_personne, nom_civil, prenom, est_expert FROM "Personne" WHERE lower(email) = lower(:email)'),
        {"email": email},
    ).mappings().first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucune fiche personnelle liée à cette invitation.")
    if role in {"gestionnaire_case", "expert_jury", "accompagnant"} and not person["est_expert"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invitation expert invalide.")

    existing_account = db.execute(
        text('SELECT 1 FROM "CompteUtilisateur" WHERE lower(email) = lower(:email)'),
        {"email": email},
    ).first()
    if existing_account:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Un compte existe déjà pour cette adresse e-mail.")

    id_role = role_id_by_name[role]

    account = db.execute(
        text('''
            INSERT INTO "CompteUtilisateur" (email, nom_affichage, mot_de_passe_hash, id_role, id_personne)
            VALUES (:email, :display_name, :password_hash, :id_role, :id_personne)
            RETURNING id_utilisateur
        '''),
        {
            "email": email,
            "display_name": f"{person['prenom']} {person['nom_civil']}".strip(),
            "password_hash": get_password_hash(data.password),
            "id_role": id_role,
            "id_personne": person["id_personne"],
        },
    ).mappings().one()
    db.execute(
        text('DELETE FROM "InvitationCompte" WHERE id_personne = :id_personne'),
        {"id_personne": person["id_personne"]},
    )
    db.commit()

    access_token = create_access_token({
        "sub": str(account["id_utilisateur"]),
        "role": role,
        "id_personne": person["id_personne"],
    })
    return {"access_token": access_token, "token_type": "bearer", "role": role}