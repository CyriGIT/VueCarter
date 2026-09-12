# Taxonomie des styles musicaux (arbre à 3 niveaux : racine FCMA -> macro-genre -> sous-genre)

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend_etl.core.dependencies import get_current_user
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur
from backend_etl.schemas.style import StyleOut

router = APIRouter(prefix="/styles", tags=["Styles Musicaux"])


@router.get("", response_model=list[StyleOut])
def get_styles(
    db: Session = Depends(get_db),
    current_user: Utilisateur = Depends(get_current_user),
):
    rows = db.execute(text('''
        SELECT id_style AS id, nom_style AS nom, id_style_parent AS "idParent"
        FROM "StyleMusical"
        WHERE est_actif
        ORDER BY id_style
    ''')).mappings().all()
    return [dict(row) for row in rows]
