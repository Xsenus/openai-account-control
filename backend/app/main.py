"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import accounts, auth, dashboard, scans, settings as settings_routes, system
from .config import settings
from .db import AsyncSessionFactory, init_db
from .services.admin_auth_service import AdminAuthService
from .services.auth_job_service import AuthJobService
from .services.panel_user_service import PanelUserService
from .services.scan_service import ScanService
from .services.scheduler_service import SchedulerService
from .services.settings_service import SettingsService

settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.evidence_dir.mkdir(parents=True, exist_ok=True)

PUBLIC_API_PREFIXES = ("/api/auth",)
PUBLIC_API_PATHS = {"/api/health"}


def is_public_request(path: str) -> bool:
    """Return whether a path should stay reachable before panel login."""
    if path in {"/api", "/evidence"}:
        return False

    if path in PUBLIC_API_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_API_PREFIXES):
        return True

    if path.startswith("/api/") or path.startswith("/evidence/"):
        return False

    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database, services, and periodic scheduler on startup."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.evidence_dir.mkdir(parents=True, exist_ok=True)

    await init_db()

    async with AsyncSessionFactory() as session:
        panel_users = PanelUserService(session)
        await panel_users.ensure_bootstrap_user()

        runtime_settings_service = SettingsService(session)
        await runtime_settings_service.ensure_defaults()
        runtime_settings = await runtime_settings_service.get()

    scan_service = ScanService()
    scheduler_service = SchedulerService(scan_service)
    auth_job_service = AuthJobService()
    admin_auth_service = AdminAuthService(AsyncSessionFactory)

    app.state.scan_service = scan_service
    app.state.scheduler_service = scheduler_service
    app.state.auth_job_service = auth_job_service
    app.state.admin_auth_service = admin_auth_service

    if settings.scheduler_enabled:
        await scheduler_service.start(runtime_settings.scan_interval_minutes)

    try:
        yield
    finally:
        await scheduler_service.stop()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# During local frontend development Vite runs on another port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        settings.frontend_public_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_panel_auth(request: Request, call_next):
    """Protect API and evidence routes with the configured admin login."""
    if request.method == "OPTIONS" or not settings.auth_enabled or is_public_request(request.url.path):
        return await call_next(request)

    auth_service = getattr(request.app.state, "admin_auth_service", None)
    token = request.cookies.get(settings.session_cookie_name)
    session = await auth_service.get_session(token) if auth_service else None
    if session is None:
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})

    request.state.admin_session = session
    return await call_next(request)


app.include_router(auth.router)
app.include_router(system.router)
app.include_router(dashboard.router)
app.include_router(accounts.router)
app.include_router(scans.router)
app.include_router(settings_routes.router)

# Mount evidence so the operator can inspect screenshots directly in the UI if needed.
app.mount("/evidence", StaticFiles(directory=str(settings.evidence_dir)), name="evidence")

# If the React frontend is built into backend/app/static, serve it as the default app shell.
frontend_dist = Path(__file__).parent / "static"
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_index() -> FileResponse:
        return FileResponse(frontend_dist / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend_app(full_path: str) -> FileResponse:
        if full_path.startswith("api/") or full_path == "api":
            raise HTTPException(status_code=404, detail="API route not found.")
        if full_path.startswith("evidence/") or full_path == "evidence":
            raise HTTPException(status_code=404, detail="Evidence route not found.")

        requested_path = frontend_dist / full_path
        if requested_path.is_file():
            return FileResponse(requested_path)

        return FileResponse(frontend_dist / "index.html")
