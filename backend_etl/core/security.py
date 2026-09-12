from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt
import bcrypt
from backend_etl.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Génère un JWT standard de session (durée courte/moyenne, ex. 24h)."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_account_token(email: str, role: str = "artiste", expires_delta: Optional[timedelta] = None) -> str:
    """Génère un jeton signé temporaire pour valider une inscription ou inviter un membre."""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=7))
    payload = {
        "sub": email,
        "role": role,
        "type": "account_creation",
        "exp": expire
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)