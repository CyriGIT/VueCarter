from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database.session import get_db
from core.dependencies import require_expert
from models.user import Utilisateur

router = APIRouter(prefix="/evaluation", tags=["Evaluation Expert"])

@router.get("/cockpit/{project_id}")
def get_project_cockpit(
    project_id: int, 
    db: Session = Depends(get_db), 
    current_expert: Utilisateur = Depends(require_expert)
):
    return {"message": f"Données confidentielles du projet {project_id} chargées par {current_expert.email}"}