from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

# Core services
from app.services.auth_service import ensure_admin_user
from app.services.module_loader_service import load_modules_on_startup
from db.session import SessionLocal

# -----------------------------------------------------
# Core API Routers (these currently live in /api/routes)
# -----------------------------------------------------
from api.routes import (
    ai,
    auth,
    bulk_upload,
    botops,
    cases,
    consent,
    deals,
    documents,
    referral,
    training,
    properties,
    auction_imports,
    leads,
    workflow,
    partner_api,
    impact_api,
    foreclosure,
    partners_housing,
    portfolio,
    membership,
    pipeline,
    verify,
)

# -----------------------------------------------------
# Admin/Member Routers (these live in /app/api/routes)
# -----------------------------------------------------
from app.api.routes import (
    admin_ai,
    admin_dashboard,
    member_dashboard,
    member_payments,
    public_apply,
    system_admin,
)

# Webhooks (these live in /app/routers)
from app.routers import webhooks


app = FastAPI()


# =====================================================
# Frontend Static Mount
# =====================================================
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/")
def read_root():
    return FileResponse(frontend_dir / "index.html")


@app.get("/styles.css")
def read_styles():
    return FileResponse(frontend_dir / "styles.css")


@app.get("/app.js")
def read_app_js():
    return FileResponse(frontend_dir / "app.js")


@app.get("/config.js")
def read_config():
    api_base = os.getenv("VITE_API_BASE_URL", "").strip()
    js = f'window.__API_BASE_URL__ = "{api_base}";'
    return Response(content=js, media_type="application/javascript")


# =====================================================
# Register Routers
# =====================================================
app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(bulk_upload.router)
app.include_router(botops.router)
app.include_router(cases.router)
app.include_router(consent.router)
app.include_router(deals.router)
app.include_router(documents.router)
app.include_router(referral.router)
app.include_router(training.router)
app.include_router(properties.router)
app.include_router(auction_imports.router)
app.include_router(leads.router)
app.include_router(workflow.router)
app.include_router(partner_api.router)
app.include_router(impact_api.router)
app.include_router(foreclosure.router)
app.include_router(partners_housing.router)
app.include_router(portfolio.router)
app.include_router(membership.router)
app.include_router(pipeline.router)
app.include_router(verify.router)

app.include_router(public_apply.router)
app.include_router(system_admin.router)
app.include_router(admin_ai.router)
app.include_router(admin_dashboard.router)
app.include_router(member_dashboard.router)
app.include_router(member_payments.router)

app.include_router(webhooks.router)


# =====================================================
# Admin System Page
# =====================================================
@app.get("/admin/system")
def admin_system_page():
    return FileResponse(frontend_dir / "admin-system.html")


@app.on_event("startup")
def bootstrap_admin_user() -> None:
    db = SessionLocal()
    try:
        ensure_admin_user(db)
    finally:
        db.close()

    # Safe dynamic module activation (Phase 8 loader foundation)
    load_modules_on_startup(app)
