from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.orm import Session
from backend_etl.core.config import settings
from backend_etl.database.session import get_db
from backend_etl.models.user import Utilisateur

# Schéma OAuth2 pointant vers la route de connexion
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> Utilisateur:
    """Valide le token JWT et récupère l'utilisateur connecté en base."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou session expirée.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(Utilisateur).filter(Utilisateur.id_utilisateur == int(user_id)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur inactif ou introuvable."
        )
    return user


def require_expert(
    current_user: Utilisateur = Depends(get_current_user)
) -> Utilisateur:
    """Restreint l'accès aux accompagnants de la Case à Chocs et aux jurys Embrayage."""
    if current_user.role not in ["gestionnaire_case", "expert_jury", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux accompagnants de la Case à Chocs."
        )
    return current_user


def require_artist(
    current_user: Utilisateur = Depends(get_current_user)
) -> Utilisateur:
    """Vérifie que l'utilisateur connecté possède le profil artiste."""
    if current_user.role not in ["artiste", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux artistes."
        )
    return current_user


def require_admin(
    current_user: Utilisateur = Depends(get_current_user)
) -> Utilisateur:
    """Restreint l'accès aux administrateurs actifs."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs."
        )
    return current_user


def require_grant_manager(
    current_user: Utilisateur = Depends(get_current_user)
) -> Utilisateur:
    """Autorise l'administration des échéances de subvention."""
    if current_user.role not in ["admin", "gestionnaire_case"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé à l’administration et aux gestionnaires de la Case à Chocs."
        )
    return current_user