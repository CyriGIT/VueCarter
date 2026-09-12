from fastapi import APIRouter, Depends
from core.dependencies import get_current_user
from models.user import Utilisateur

router = APIRouter(prefix="/projects", tags=["Projets Musicaux"])

@router.get("/me")
def get_my_projects(current_user: Utilisateur = Depends(get_current_user)):
    return {"user_id": current_user.id_utilisateur, "role": current_user.role}