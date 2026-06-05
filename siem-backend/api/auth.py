import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "ChangeMe_JWT_At_Least_32_Chars_2026")
ALGORITHM = "HS256"

USERS = {
    os.getenv("SIEM_ADMIN_USER", "admin"): {
        "username": os.getenv("SIEM_ADMIN_USER", "admin"),
        "password_hash": pwd_context.hash(os.getenv("SIEM_ADMIN_PASSWORD", "ChangeMe_SIEM_2026")),
        "role": "Admin",
    },
    "analyst": {"username": "analyst", "password_hash": pwd_context.hash("analyst123"), "role": "Analyst"},
    "viewer": {"username": "viewer", "password_hash": pwd_context.hash("viewer123"), "role": "Viewer"},
}


def create_access_token(username: str, role: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": username, "role": role, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/token")
def token(form: OAuth2PasswordRequestForm = Depends()):
    user = USERS.get(form.username)
    if not user or not pwd_context.verify(form.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return {"access_token": create_access_token(user["username"], user["role"]), "token_type": "bearer", "role": user["role"]}


def current_user(token_value: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token_value, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        role = payload.get("role")
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if not username or username not in USERS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown user")
    return {"username": username, "role": role}


def require_role(*roles: str):
    def dependency(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency
