# Profil de la personne connectée (fiche "Personne" liée au compte utilisateur)

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend_etl.core.dependencies import get_current_user
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur
from backend_etl.schemas.user import AccountIdentityResponse, PersonUpdateRequest
from backend_etl.services.account_identity_service import resolve_display_name

router = APIRouter(prefix="/me", tags=["Profil"])

PERSON_SELECT_COLUMNS = '''
    id_personne AS id, nom_civil AS nom, prenom,
    date_naissance AS "dateNaissance", genre, adresse, npa,
    ville, canton, telephone, email
'''


@router.get("/account", response_model=AccountIdentityResponse)
def get_my_account_identity(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    account = db.execute(
        text('''
            SELECT cu.id_utilisateur AS id,
                   cu.email,
                   cu.nom_affichage AS "displayName",
                   pe.prenom AS "firstName",
                   pe.nom_civil AS "lastName",
                   cu.id_personne AS "personId"
            FROM "CompteUtilisateur" cu
            LEFT JOIN "Personne" pe ON pe.id_personne = cu.id_personne
            WHERE cu.id_utilisateur = :user_id
        '''),
        {"user_id": current_user.id_utilisateur},
    ).mappings().first()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compte utilisateur introuvable.")

    return {
        **dict(account),
        "displayName": resolve_display_name(
            account["displayName"],
            account["firstName"],
            account["lastName"],
            account["email"],
        ),
        "role": current_user.role,
        "canManageEvaluations": current_user.role == "gestionnaire_case",
    }


@router.get("")
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    if not current_user.id_personne:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune fiche personnelle liée à ce compte.",
        )

    person = db.execute(
        text(f'SELECT {PERSON_SELECT_COLUMNS} FROM "Personne" WHERE id_personne = :id_personne'),
        {"id_personne": current_user.id_personne},
    ).mappings().first()

    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fiche personnelle introuvable.")

    return dict(person)


@router.put("")
def update_my_profile(
    payload: PersonUpdateRequest,
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    if not current_user.id_personne:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune fiche personnelle liée à ce compte.",
        )

    existing_email = db.execute(
        text('''
            SELECT 1 FROM "Personne"
            WHERE lower(email) = lower(:email) AND id_personne != :id_personne
        '''),
        {"email": payload.email, "id_personne": current_user.id_personne},
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette adresse e-mail est déjà utilisée par un autre compte.",
        )

    updated_person = db.execute(
        text(f'''
            UPDATE "Personne"
            SET nom_civil = :nom_civil,
                prenom = :prenom,
                date_naissance = :date_naissance,
                genre = :genre,
                adresse = :adresse,
                npa = :npa,
                ville = :ville,
                canton = :canton,
                telephone = :telephone,
                email = :email
            WHERE id_personne = :id_personne
            RETURNING {PERSON_SELECT_COLUMNS}
        '''),
        {
            "nom_civil": payload.nom_civil,
            "prenom": payload.prenom,
            "date_naissance": payload.date_naissance,
            "genre": payload.genre,
            "adresse": payload.adresse,
            "npa": payload.npa,
            "ville": payload.ville,
            "canton": payload.canton,
            "telephone": payload.telephone,
            "email": payload.email,
            "id_personne": current_user.id_personne,
        },
    ).mappings().first()
    db.commit()

    return dict(updated_person)
