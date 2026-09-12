from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend_etl.core.dependencies import require_admin
from backend_etl.core.security import create_account_token
from backend_etl.database.session import get_db
from backend_etl.schemas.admin import (
    FormationOut,
    FormationUpdate,
    FormationWrite,
    ExpertInvitationWrite,
    ExpertOut,
    ExpertRoleWrite,
    ExpertUpdate,
    InvitationOut,
    LegalStatusOut,
    LegalStatusUpdate,
    LegalStatusWrite,
    PhaseTypeOut,
    PhaseTypeUpdate,
    PhaseTypeWrite,
    PlatformOut,
    PlatformUpdate,
    PlatformWrite,
    ProfessionalStructureOut,
    ProfessionalStructureUpdate,
    ProfessionalStructureWrite,
    ProgramOut,
    ProgramUpdate,
    ProgramWrite,
    StyleAdminOut,
    StyleUpdate,
    StyleWrite,
    VenueAdminOut,
    VenueAdminUpdate,
    VenueAdminWrite,
)

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(require_admin)],
)


def _write(db: Session, statement: str, params: dict, not_found: str | None = None):
    try:
        row = db.execute(text(statement), params).mappings().first()
        if row is None and not_found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found)
        db.commit()
        return dict(row) if row else None
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une entrée équivalente existe déjà ou cette modification viole une contrainte.",
        ) from error


def _invitation_url(email: str, role: str) -> str:
    token = create_account_token(email, role)
    return f"/invite?token={quote(token, safe='')}"


def _expert_row(db: Session, person_id: int):
    return db.execute(text('''
        SELECT personne.id_personne AS id, personne.prenom, personne.nom_civil AS nom,
               personne.email, personne.date_naissance AS "dateNaissance", personne.genre,
               personne.npa, personne.ville, personne.telephone,
               COALESCE(
                   invitation.role_invite,
                   CASE compte.id_role WHEN 2 THEN 'gestionnaire_case' WHEN 3 THEN 'expert_jury' WHEN 5 THEN 'accompagnant' END
               ) AS role,
               CASE
                   WHEN compte.id_utilisateur IS NULL THEN 'pending'
                   WHEN compte.est_actif THEN 'active'
                   ELSE 'inactive'
               END AS statut
        FROM "Personne" personne
        LEFT JOIN "CompteUtilisateur" compte ON compte.id_personne = personne.id_personne
        LEFT JOIN "InvitationCompte" invitation ON invitation.id_personne = personne.id_personne
        WHERE personne.id_personne = :person_id
          AND (invitation.id_personne IS NOT NULL OR compte.id_role IN (2, 3, 5))
    '''), {"person_id": person_id}).mappings().first()


@router.get("/experts", response_model=list[ExpertOut])
def list_experts(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT personne.id_personne AS id, personne.prenom, personne.nom_civil AS nom,
               personne.email, personne.date_naissance AS "dateNaissance", personne.genre,
               personne.npa, personne.ville, personne.telephone,
               COALESCE(
                   invitation.role_invite,
                   CASE compte.id_role WHEN 2 THEN 'gestionnaire_case' WHEN 3 THEN 'expert_jury' WHEN 5 THEN 'accompagnant' END
               ) AS role,
               CASE
                   WHEN compte.id_utilisateur IS NULL THEN 'pending'
                   WHEN compte.est_actif THEN 'active'
                   ELSE 'inactive'
               END AS statut
        FROM "Personne" personne
        LEFT JOIN "CompteUtilisateur" compte ON compte.id_personne = personne.id_personne
        LEFT JOIN "InvitationCompte" invitation ON invitation.id_personne = personne.id_personne
        WHERE invitation.id_personne IS NOT NULL OR compte.id_role IN (2, 3, 5)
        ORDER BY lower(personne.nom_civil), lower(personne.prenom)
    ''')).mappings().all()


@router.post("/experts/invitations", response_model=InvitationOut, status_code=201)
def create_expert_invitation(payload: ExpertInvitationWrite, db: Session = Depends(get_db)):
    try:
        if db.execute(text('''
            SELECT 1 FROM "Personne" WHERE lower(email) = lower(:email)
            UNION ALL
            SELECT 1 FROM "CompteUtilisateur" WHERE lower(email) = lower(:email)
        '''), {"email": str(payload.email)}).first():
            raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée.")
        person_id = db.execute(text('''
            INSERT INTO "Personne" (
                nom_civil, prenom, date_naissance, genre, npa, ville,
                telephone, email, est_expert
            ) VALUES (
                trim(:nom), trim(:prenom), :dateNaissance, :genre, trim(:npa),
                trim(:ville), :telephone, lower(:email), TRUE
            ) RETURNING id_personne
        '''), payload.model_dump(mode="json")).scalar_one()
        db.execute(text('''
            INSERT INTO "InvitationCompte" (id_personne, role_invite)
            VALUES (:person_id, :role)
        '''), {"person_id": person_id, "role": payload.role})
        db.commit()
        return {
            "personId": person_id,
            "invitationUrl": _invitation_url(str(payload.email), payload.role),
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette invitation existe déjà.") from error


@router.post("/experts/{person_id}/invitation", response_model=InvitationOut)
def renew_expert_invitation(
    person_id: int,
    payload: ExpertRoleWrite,
    db: Session = Depends(get_db),
):
    person = db.execute(text('''
        SELECT personne.email
        FROM "Personne" personne
        LEFT JOIN "CompteUtilisateur" compte ON compte.id_personne = personne.id_personne
        WHERE personne.id_personne = :person_id
          AND personne.est_expert
          AND compte.id_utilisateur IS NULL
    '''), {"person_id": person_id}).mappings().first()
    if not person:
        raise HTTPException(status_code=409, detail="Cette invitation ne peut pas être régénérée.")
    _write(db, '''
        INSERT INTO "InvitationCompte" (id_personne, role_invite)
        VALUES (:person_id, :role)
        ON CONFLICT (id_personne) DO UPDATE
        SET role_invite = EXCLUDED.role_invite, date_invitation = CURRENT_TIMESTAMP
        RETURNING id_personne AS id
    ''', {"person_id": person_id, "role": payload.role})
    return {
        "personId": person_id,
        "invitationUrl": _invitation_url(person["email"], payload.role),
    }


@router.patch("/experts/{person_id}", response_model=ExpertOut)
def update_expert(person_id: int, payload: ExpertUpdate, db: Session = Depends(get_db)):
    existing = _expert_row(db, person_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Expert introuvable.")
    role_id = {"gestionnaire_case": 2, "expert_jury": 3, "accompagnant": 5}[payload.role]
    try:
        db.execute(text('''
            UPDATE "Personne"
            SET nom_civil = trim(:nom), prenom = trim(:prenom), email = lower(:email),
                date_naissance = :dateNaissance, genre = :genre, npa = trim(:npa),
                ville = trim(:ville), telephone = :telephone, est_expert = TRUE
            WHERE id_personne = :person_id
        '''), {**payload.model_dump(mode="json"), "person_id": person_id})
        account = db.execute(text('''
            UPDATE "CompteUtilisateur"
            SET email = lower(:email), nom_affichage = trim(:prenom) || ' ' || trim(:nom),
                id_role = :role_id, est_actif = :estActif
            WHERE id_personne = :person_id
            RETURNING id_utilisateur
        '''), {**payload.model_dump(mode="json"), "person_id": person_id, "role_id": role_id}).first()
        if account is None:
            if not payload.estActif:
                raise HTTPException(status_code=409, detail="Un compte en attente ne peut pas être désactivé.")
            db.execute(text('''
                UPDATE "InvitationCompte" SET role_invite = :role
                WHERE id_personne = :person_id
            '''), {"person_id": person_id, "role": payload.role})
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="Cette adresse e-mail est déjà utilisée.") from error
    return dict(_expert_row(db, person_id))


@router.get("/legal-statuses", response_model=list[LegalStatusOut])
def list_legal_statuses(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT id_statut_juridique AS id, libelle_statut AS libelle, est_actif AS "estActif"
        FROM "StatutJuridique"
        ORDER BY est_actif DESC, lower(libelle_statut)
    ''')).mappings().all()


@router.post("/legal-statuses", response_model=LegalStatusOut, status_code=status.HTTP_201_CREATED)
def create_legal_status(payload: LegalStatusWrite, db: Session = Depends(get_db)):
    return _write(db, '''
        INSERT INTO "StatutJuridique" (libelle_statut)
        VALUES (trim(:libelle))
        RETURNING id_statut_juridique AS id, libelle_statut AS libelle, est_actif AS "estActif"
    ''', payload.model_dump())


@router.patch("/legal-statuses/{item_id}", response_model=LegalStatusOut)
def update_legal_status(item_id: int, payload: LegalStatusUpdate, db: Session = Depends(get_db)):
    return _write(db, '''
        UPDATE "StatutJuridique"
        SET libelle_statut = trim(:libelle), est_actif = :estActif
        WHERE id_statut_juridique = :id
        RETURNING id_statut_juridique AS id, libelle_statut AS libelle, est_actif AS "estActif"
    ''', {**payload.model_dump(), "id": item_id}, "Statut juridique introuvable.")


@router.get("/phase-types", response_model=list[PhaseTypeOut])
def list_phase_types(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT id_type_phase AS id, nom_phase AS nom, est_actif AS "estActif"
        FROM "TypePhaseProjet"
        ORDER BY est_actif DESC, lower(nom_phase)
    ''')).mappings().all()


@router.post("/phase-types", response_model=PhaseTypeOut, status_code=status.HTTP_201_CREATED)
def create_phase_type(payload: PhaseTypeWrite, db: Session = Depends(get_db)):
    return _write(db, '''
        INSERT INTO "TypePhaseProjet" (nom_phase)
        VALUES (trim(:nom))
        RETURNING id_type_phase AS id, nom_phase AS nom, est_actif AS "estActif"
    ''', payload.model_dump())


@router.patch("/phase-types/{item_id}", response_model=PhaseTypeOut)
def update_phase_type(item_id: int, payload: PhaseTypeUpdate, db: Session = Depends(get_db)):
    return _write(db, '''
        UPDATE "TypePhaseProjet"
        SET nom_phase = trim(:nom), est_actif = :estActif
        WHERE id_type_phase = :id
        RETURNING id_type_phase AS id, nom_phase AS nom, est_actif AS "estActif"
    ''', {**payload.model_dump(), "id": item_id}, "Type de phase introuvable.")


def _validate_style_parent(db: Session, style_id: int | None, parent_id: int | None) -> None:
    if parent_id is None:
        return
    if style_id == parent_id:
        raise HTTPException(status_code=422, detail="Un style ne peut pas être son propre parent.")
    parent = db.execute(text('''
        SELECT est_actif FROM "StyleMusical" WHERE id_style = :parent_id
    '''), {"parent_id": parent_id}).mappings().first()
    if not parent:
        raise HTTPException(status_code=422, detail="Style parent introuvable.")
    if not parent["est_actif"]:
        raise HTTPException(status_code=422, detail="Le style parent doit être actif.")
    if style_id is not None:
        creates_cycle = db.execute(text('''
            WITH RECURSIVE descendants AS (
                SELECT id_style FROM "StyleMusical" WHERE id_style_parent = :style_id
                UNION ALL
                SELECT child.id_style
                FROM "StyleMusical" child
                JOIN descendants parent ON child.id_style_parent = parent.id_style
            )
            SELECT 1 FROM descendants WHERE id_style = :parent_id
        '''), {"style_id": style_id, "parent_id": parent_id}).first()
        if creates_cycle:
            raise HTTPException(status_code=422, detail="Cette hiérarchie créerait un cycle.")


@router.get("/styles", response_model=list[StyleAdminOut])
def list_styles(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT id_style AS id, nom_style AS nom, id_style_parent AS "parentId", est_actif AS "estActif"
        FROM "StyleMusical"
        ORDER BY est_actif DESC, lower(nom_style)
    ''')).mappings().all()


@router.post("/styles", response_model=StyleAdminOut, status_code=status.HTTP_201_CREATED)
def create_style(payload: StyleWrite, db: Session = Depends(get_db)):
    _validate_style_parent(db, None, payload.parentId)
    return _write(db, '''
        INSERT INTO "StyleMusical" (nom_style, id_style_parent)
        VALUES (trim(:nom), :parentId)
        RETURNING id_style AS id, nom_style AS nom, id_style_parent AS "parentId", est_actif AS "estActif"
    ''', payload.model_dump())


@router.patch("/styles/{item_id}", response_model=StyleAdminOut)
def update_style(item_id: int, payload: StyleUpdate, db: Session = Depends(get_db)):
    _validate_style_parent(db, item_id, payload.parentId)
    if not payload.estActif:
        active_child = db.execute(text('''
            SELECT 1 FROM "StyleMusical" WHERE id_style_parent = :id AND est_actif
        '''), {"id": item_id}).first()
        if active_child:
            raise HTTPException(status_code=409, detail="Désactivez d'abord les styles enfants.")
    return _write(db, '''
        UPDATE "StyleMusical"
        SET nom_style = trim(:nom), id_style_parent = :parentId, est_actif = :estActif
        WHERE id_style = :id
        RETURNING id_style AS id, nom_style AS nom, id_style_parent AS "parentId", est_actif AS "estActif"
    ''', {**payload.model_dump(), "id": item_id}, "Style introuvable.")


@router.get("/programs", response_model=list[ProgramOut])
def list_programs(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT id_programme AS id, nom_programme AS nom,
               organisme_organisateur AS organisme, est_actif AS "estActif"
        FROM "ProgrammeAccompagnement"
        ORDER BY est_actif DESC, lower(nom_programme)
    ''')).mappings().all()


@router.post("/programs", response_model=ProgramOut, status_code=201)
def create_program(payload: ProgramWrite, db: Session = Depends(get_db)):
    return _write(db, '''
        INSERT INTO "ProgrammeAccompagnement" (nom_programme, organisme_organisateur)
        VALUES (trim(:nom), NULLIF(trim(:organisme), ''))
        RETURNING id_programme AS id, nom_programme AS nom,
                  organisme_organisateur AS organisme, est_actif AS "estActif"
    ''', payload.model_dump())


@router.patch("/programs/{item_id}", response_model=ProgramOut)
def update_program(item_id: int, payload: ProgramUpdate, db: Session = Depends(get_db)):
    return _write(db, '''
        UPDATE "ProgrammeAccompagnement"
        SET nom_programme = trim(:nom), organisme_organisateur = NULLIF(trim(:organisme), ''),
            est_actif = :estActif
        WHERE id_programme = :id
        RETURNING id_programme AS id, nom_programme AS nom,
                  organisme_organisateur AS organisme, est_actif AS "estActif"
    ''', {**payload.model_dump(), "id": item_id}, "Programme introuvable.")


@router.get("/formations", response_model=list[FormationOut])
def list_formations(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT id_formation AS id, nom_formation AS nom,
               organisme_formateur AS organisme, est_actif AS "estActif"
        FROM "Formation"
        ORDER BY est_actif DESC, lower(nom_formation)
    ''')).mappings().all()


@router.post("/formations", response_model=FormationOut, status_code=201)
def create_formation(payload: FormationWrite, db: Session = Depends(get_db)):
    return _write(db, '''
        INSERT INTO "Formation" (nom_formation, organisme_formateur)
        VALUES (trim(:nom), NULLIF(trim(:organisme), ''))
        RETURNING id_formation AS id, nom_formation AS nom,
                  organisme_formateur AS organisme, est_actif AS "estActif"
    ''', payload.model_dump())


@router.patch("/formations/{item_id}", response_model=FormationOut)
def update_formation(item_id: int, payload: FormationUpdate, db: Session = Depends(get_db)):
    return _write(db, '''
        UPDATE "Formation"
        SET nom_formation = trim(:nom), organisme_formateur = NULLIF(trim(:organisme), ''),
            est_actif = :estActif
        WHERE id_formation = :id
        RETURNING id_formation AS id, nom_formation AS nom,
                  organisme_formateur AS organisme, est_actif AS "estActif"
    ''', {**payload.model_dump(), "id": item_id}, "Formation introuvable.")


@router.get("/professional-structures", response_model=list[ProfessionalStructureOut])
def list_professional_structures(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT id_structure AS id, nom_structure AS nom, type_structure AS type,
               contact_email AS email, pays, est_actif AS "estActif"
        FROM "StructureProfessionnelle"
        ORDER BY est_actif DESC, lower(nom_structure)
    ''')).mappings().all()


@router.post("/professional-structures", response_model=ProfessionalStructureOut, status_code=201)
def create_professional_structure(payload: ProfessionalStructureWrite, db: Session = Depends(get_db)):
    return _write(db, '''
        INSERT INTO "StructureProfessionnelle" (nom_structure, type_structure, contact_email, pays)
        VALUES (trim(:nom), :type, :email, trim(:pays))
        RETURNING id_structure AS id, nom_structure AS nom, type_structure AS type,
                  contact_email AS email, pays, est_actif AS "estActif"
    ''', payload.model_dump(mode="json"))


@router.patch("/professional-structures/{item_id}", response_model=ProfessionalStructureOut)
def update_professional_structure(item_id: int, payload: ProfessionalStructureUpdate, db: Session = Depends(get_db)):
    return _write(db, '''
        UPDATE "StructureProfessionnelle"
        SET nom_structure = trim(:nom), type_structure = :type, contact_email = :email,
            pays = trim(:pays), est_actif = :estActif
        WHERE id_structure = :id
        RETURNING id_structure AS id, nom_structure AS nom, type_structure AS type,
                  contact_email AS email, pays, est_actif AS "estActif"
    ''', {**payload.model_dump(mode="json"), "id": item_id}, "Structure introuvable.")


@router.get("/venues", response_model=list[VenueAdminOut])
def list_venues(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT id_venue AS id, nom_venue AS nom, adresse, ville, npa, pays,
               valeur_pairs AS jauge, est_festival AS "estFestival", est_actif AS "estActif"
        FROM "Venue"
        ORDER BY est_actif DESC, lower(nom_venue), lower(ville)
    ''')).mappings().all()


@router.post("/venues", response_model=VenueAdminOut, status_code=201)
def create_venue(payload: VenueAdminWrite, db: Session = Depends(get_db)):
    return _write(db, '''
        INSERT INTO "Venue" (nom_venue, adresse, ville, npa, pays, valeur_pairs, est_festival)
        VALUES (trim(:nom), :adresse, trim(:ville), :npa, trim(:pays), :jauge, :estFestival)
        RETURNING id_venue AS id, nom_venue AS nom, adresse, ville, npa, pays,
                  valeur_pairs AS jauge, est_festival AS "estFestival", est_actif AS "estActif"
    ''', payload.model_dump())


@router.patch("/venues/{item_id}", response_model=VenueAdminOut)
def update_venue(item_id: int, payload: VenueAdminUpdate, db: Session = Depends(get_db)):
    return _write(db, '''
        UPDATE "Venue"
        SET nom_venue = trim(:nom), adresse = :adresse, ville = trim(:ville), npa = :npa,
            pays = trim(:pays), valeur_pairs = :jauge, est_festival = :estFestival,
            est_actif = :estActif
        WHERE id_venue = :id
        RETURNING id_venue AS id, nom_venue AS nom, adresse, ville, npa, pays,
                  valeur_pairs AS jauge, est_festival AS "estFestival", est_actif AS "estActif"
    ''', {**payload.model_dump(), "id": item_id}, "Salle introuvable.")


@router.get("/platforms", response_model=list[PlatformOut])
def list_platforms(db: Session = Depends(get_db)):
    return db.execute(text('''
        SELECT id_plateforme AS id, nom_plateforme AS nom, type_plateforme AS type,
               est_actif AS "estActif"
        FROM "Plateforme"
        ORDER BY est_actif DESC, lower(nom_plateforme)
    ''')).mappings().all()


@router.post("/platforms", response_model=PlatformOut, status_code=201)
def create_platform(payload: PlatformWrite, db: Session = Depends(get_db)):
    return _write(db, '''
        INSERT INTO "Plateforme" (nom_plateforme, type_plateforme)
        VALUES (trim(:nom), trim(:type))
        RETURNING id_plateforme AS id, nom_plateforme AS nom, type_plateforme AS type,
                  est_actif AS "estActif"
    ''', payload.model_dump())


@router.patch("/platforms/{item_id}", response_model=PlatformOut)
def update_platform(item_id: int, payload: PlatformUpdate, db: Session = Depends(get_db)):
    return _write(db, '''
        UPDATE "Plateforme"
        SET nom_plateforme = trim(:nom), type_plateforme = trim(:type), est_actif = :estActif
        WHERE id_plateforme = :id
        RETURNING id_plateforme AS id, nom_plateforme AS nom, type_plateforme AS type,
                  est_actif AS "estActif"
    ''', {**payload.model_dump(), "id": item_id}, "Plateforme introuvable.")