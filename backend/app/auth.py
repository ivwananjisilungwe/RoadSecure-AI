import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import Lock
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import AuditLog, LoginSession, User
from .schemas import Login

SESSION_COOKIE = "roadsecure_session"
SESSION_SECONDS = 8 * 60 * 60
TOKEN_ISSUER = "roadsecure-ai"
password_hash = PasswordHash.recommended()
router = APIRouter(prefix="/auth", tags=["Authentication"])


def load_signing_key(directory: Path):
    key_path = directory / "jwt.key"
    if not key_path.exists():
        with NamedTemporaryFile(dir=directory, delete=False) as temporary:
            temporary.write(secrets.token_hex(32).encode("ascii"))
            temporary_path = Path(temporary.name)
        try:
            os.link(temporary_path, key_path)
        except FileExistsError:
            pass
        finally:
            temporary_path.unlink(missing_ok=True)
    key = key_path.read_text(encoding="ascii").strip()
    if len(key) != 64 or any(character not in "0123456789abcdef" for character in key):
        raise RuntimeError("The local JWT signing key is invalid")
    return key


def bootstrap_admin(session_factory):
    with session_factory.begin() as db:
        if db.scalar(select(User.id).where(User.role == "ADMIN")) is not None:
            return

        username = os.environ.get("ROADSECURE_ADMIN_USERNAME", "admin")
        password = os.environ.get("ROADSECURE_ADMIN_PASSWORD", "")
        if not 12 <= len(password) <= 256:
            raise RuntimeError("Set ROADSECURE_ADMIN_PASSWORD to 12–256 characters for first startup")
        credentials = Login(username=username, password=password)
        db.add(User(username=credentials.username, password_hash=password_hash.hash(password)))


def get_db(request: Request):
    with request.app.state.session_factory() as db:
        yield db


Database = Annotated[Session, Depends(get_db)]


def user_data(user: User):
    return {"id": user.id, "username": user.username, "role": user.role}


class LoginLimiter:
    def __init__(self):
        self._attempts = defaultdict(deque)
        self._lock = Lock()

    def reserve(self, key):
        now = time.monotonic()
        with self._lock:
            for existing in list(self._attempts):
                attempts = self._attempts[existing]
                while attempts and now - attempts[0] >= 60:
                    attempts.popleft()
                if not attempts:
                    del self._attempts[existing]

            if len(self._attempts[key]) >= 12:
                raise HTTPException(429, "Too many login attempts. Try again in one minute.")
            self._attempts[key].append(now)

    def clear(self, key):
        with self._lock:
            self._attempts.pop(key, None)


def current_session(request: Request, db: Database):
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        try:
            claims = jwt.decode(
                token,
                request.app.state.signing_key,
                algorithms=["HS256"],
                issuer=TOKEN_ISSUER,
                options={"require": ["sub", "exp", "iat", "jti", "iss"]},
            )
            session = db.get(LoginSession, claims["jti"])
            if session and str(session.user_id) == claims["sub"] and session.expires_at > time.time():
                return session
        except jwt.InvalidTokenError:
            pass
    raise HTTPException(401, "Authentication required")


LoginSessionDependency = Annotated[LoginSession, Depends(current_session)]


def current_user(session: LoginSessionDependency, db: Database):
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(401, "Authentication required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require_admin(user: CurrentUser):
    if user.role != "ADMIN":
        raise HTTPException(403, "Administrator access required")
    return user


Administrator = Annotated[User, Depends(require_admin)]


def log_action(db: Session, user_id: int | None, action: str, detail: str):
    db.add(AuditLog(user_id=user_id, action=action, detail=detail))


@router.post("/login")
def login(payload: Login, request: Request, response: Response, db: Database):
    client_key = request.client.host if request.client else "local"
    request.app.state.login_limiter.reserve(client_key)
    user = db.scalar(select(User).where(User.username == payload.username))
    hashed = user.password_hash if user else request.app.state.dummy_hash
    valid = password_hash.verify(payload.password, hashed)
    if user is None or not valid:
        log_action(db, None, "LOGIN_FAILED", "Invalid credentials")
        db.commit()
        raise HTTPException(401, "Invalid username or password")

    now = int(time.time())
    expiry = now + SESSION_SECONDS
    session_id = secrets.token_urlsafe(32)
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    db.add(LoginSession(id=session_id, user_id=user.id, expires_at=expiry))
    log_action(db, user.id, "LOGIN", "Session opened")
    db.commit()
    request.app.state.login_limiter.clear(client_key)

    token = jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": expiry, "jti": session_id, "iss": TOKEN_ISSUER},
        request.app.state.signing_key,
        algorithm="HS256",
    )
    response.set_cookie(
        SESSION_COOKIE, token, max_age=SESSION_SECONDS, httponly=True, samesite="strict",
        secure=request.app.state.secure_cookies,
    )
    return user_data(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Database, session: LoginSessionDependency):
    log_action(db, session.user_id, "LOGOUT", "Session closed")
    db.delete(session)
    db.commit()
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, samesite="strict", secure=request.app.state.secure_cookies,
    )
    return {"ok": True}


@router.get("/me")
def get_current_user(user: CurrentUser):
    return user_data(user)
