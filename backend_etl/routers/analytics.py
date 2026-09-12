from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend_etl.core.config import settings
from backend_etl.core.dependencies import get_current_user
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur
from backend_etl.schemas.analytics import MetabaseEmbedResponse


router = APIRouter(prefix="/analytics", tags=["Analytics"])


def build_metabase_dashboard_url(params: dict | None = None) -> str:
    if not settings.metabase_is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Le tableau de bord Metabase n’est pas encore configuré.",
        )

    try:
        dashboard_id = int(settings.METABASE_DASHBOARD_ID)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="L’identifiant du tableau de bord Metabase est invalide.",
        ) from error

    payload = {
        "resource": {"dashboard": dashboard_id},
        "params": params or {},
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    token = jwt.encode(payload, settings.METABASE_EMBEDDING_SECRET_KEY, algorithm="HS256")
    return f"{settings.METABASE_SITE_URL.rstrip('/')}/embed/dashboard/{token}#bordered=false&titled=false&theme=night"


@router.get("/metabase/embed", response_model=MetabaseEmbedResponse)
def get_metabase_embed_url(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in ("gestionnaire_case", "expert_jury", "accompagnant", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux experts et accompagnants.",
        )

    params = {}
    if current_user.role == "accompagnant":
        if current_user.id_personne is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Le compte accompagnant doit être lié à une personne.",
            )
        project_ids = db.execute(text('''
            SELECT id_projet
            FROM "AffectationAccompagnement"
            WHERE id_expert = :id_personne
            ORDER BY id_projet
        '''), {"id_personne": current_user.id_personne}).scalars().all()
        if not project_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Aucun projet n’est affecté à cet accompagnant.",
            )
        params = {"filtre_par_projet": project_ids}

    return {"url": build_metabase_dashboard_url(params)}