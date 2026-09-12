from sqlalchemy import text
from sqlalchemy.orm import Session


OBJECTIVE_RULE_LABELS = {
    "projet_neuchatelois": "Au moins un membre actif domicilié dans le canton de Neuchâtel",
    "membres_18_25": "Tous les membres actifs ont entre 18 et 25 ans",
    "au_moins_un_morceau_original": "Au moins un morceau est déclaré original",
    "concert_effectue": "Au moins un concert a déjà eu lieu",
    "au_moins_un_morceau": "Au moins un morceau figure au répertoire",
}


def calculate_objective_rules(db: Session, project_id: int) -> dict[str, int]:
    row = db.execute(text('''
        SELECT
            EXISTS (
                SELECT 1
                FROM "MembreProjet" membre
                JOIN "Personne" personne ON personne.id_personne = membre.id_personne
                WHERE membre.id_projet = :project_id
                  AND membre.date_depart IS NULL
                                    AND upper(trim(COALESCE(personne.canton, ''))) IN ('NE', 'NEUCHÂTEL', 'NEUCHATEL')
            ) AS projet_neuchatelois,
            EXISTS (
                SELECT 1 FROM "MembreProjet"
                WHERE id_projet = :project_id AND date_depart IS NULL
            ) AND NOT EXISTS (
                SELECT 1
                FROM "MembreProjet" membre
                JOIN "Personne" personne ON personne.id_personne = membre.id_personne
                WHERE membre.id_projet = :project_id
                  AND membre.date_depart IS NULL
                  AND (
                      personne.date_naissance IS NULL
                      OR date_part('year', age(CURRENT_DATE, personne.date_naissance)) NOT BETWEEN 18 AND 25
                  )
            ) AS membres_18_25,
            EXISTS (
                SELECT 1 FROM "Morceau"
                WHERE id_projet = :project_id AND NOT est_reprise
            ) AS au_moins_un_morceau_original,
            EXISTS (
                SELECT 1 FROM "Concert"
                WHERE id_projet = :project_id AND date_heure <= CURRENT_TIMESTAMP
            ) AS concert_effectue,
            EXISTS (
                SELECT 1 FROM "Morceau" WHERE id_projet = :project_id
            ) AS au_moins_un_morceau
    '''), {"project_id": project_id}).mappings().one()
    return {rule: int(bool(row[rule])) for rule in OBJECTIVE_RULE_LABELS}
