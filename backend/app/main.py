import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from .api import router
from .auth import Database, LoginLimiter, bootstrap_admin, load_signing_key, password_hash
from .detection import Detector
from .models import initialise_database
from .simulator import LiveSimulator, router as simulator_router

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "database" / "runtime"
MAX_BODY_BYTES = 65_536
MUTATIONS = {"POST", "PATCH", "PUT", "DELETE"}


def create_app():
    allowed_origins = frozenset(
        origin.strip() for origin in os.environ.get(
            "ROADSECURE_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000",
        ).split(",") if origin.strip()
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        directory = Path(os.environ.get("ROADSECURE_DATA_DIR", DEFAULT_DATA_DIR)).resolve()
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
        app.state.signing_key = load_signing_key(directory)
        app.state.secure_cookies = os.environ.get("ROADSECURE_SECURE_COOKIES") == "1"
        app.state.login_limiter = LoginLimiter()
        app.state.dummy_hash = password_hash.hash("roadsecure-dummy-hash")
        engine, app.state.session_factory = initialise_database(directory)
        for suffix in ("", "-wal", "-shm"):
            database_file = directory / f"roadsecure.sqlite3{suffix}"
            if database_file.exists():
                os.chmod(database_file, 0o600)
        try:
            bootstrap_admin(app.state.session_factory)
            app.state.detector = Detector.load()
            app.state.live_simulator = LiveSimulator(app.state.session_factory, app.state.detector)
            try:
                yield
            finally:
                await app.state.live_simulator.stop()
        finally:
            engine.dispose()

    app = FastAPI(title="RoadSecure AI", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"],
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=sorted(allowed_origins), allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def guard_mutations(request: Request, call_next):
        if request.method in MUTATIONS:
            origin = request.headers.get("origin")
            if origin is not None and origin not in allowed_origins:
                return JSONResponse({"detail": "Untrusted request origin"}, 403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Cross-site mutation denied"}, 403)
            length = request.headers.get("content-length", "0")
            if not length.isdecimal() or len(length) > 10 or request.headers.get("transfer-encoding"):
                return JSONResponse({"detail": "Invalid request length"}, 400)
            if int(length) > MAX_BODY_BYTES:
                return JSONResponse({"detail": "Request body is too large"}, 413)
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, exc):
        details = [
            {"loc": error["loc"], "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return JSONResponse({"detail": details}, status_code=422)

    @app.exception_handler(IntegrityError)
    @app.exception_handler(StaleDataError)
    async def data_conflict(_request, _exc):
        return JSONResponse({"detail": "The record conflicts with current data. Refresh and try again."}, 409)

    @app.get("/health", tags=["System"])
    def health(db: Database):
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "ok", "model": "loaded"}

    app.include_router(router)
    app.include_router(simulator_router, prefix="/api/v1")
    return app


app = create_app()
