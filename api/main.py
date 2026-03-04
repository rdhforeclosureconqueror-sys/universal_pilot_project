from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from db.session import SessionLocal
from app.services.auth_service import ensure_admin_user

# ✅ Import route modules explicitly (DO NOT rely on app.api.routes.__init__.py exporting them)
import app.api.routes.ai as ai
import app.api.routes.auth as auth
import app.api.routes.bulk_upload as bulk_upload
import app.api.routes.botops as botops
import app.api.routes.cases as cases
import app.api.routes.consent as consent
import app.api.routes.deals as deals
import app.api.routes.documents as documents
import app.api.routes.referral as referral
import app.api.routes.training as training
import app.api.routes.properties as properties
import app.api.routes.auction_imports as auction_imports
import app.api.routes.leads as leads
import app.api.routes.workflow as workflow
import app.api.routes.partner_api as partner_api

# Admin/member/public
import app.api.routes.admin_ai as admin_ai
import app.api.routes.admin_dashboard as admin_dashboard
import app.api.routes.member_dashboard as member_dashboard
import app.api.routes.member_payments as member_payments
import app.api.routes.public_apply as public_apply
import app.api.routes.system_admin as system_admin

# Webhooks live under app/routers
import app.routers.webhooks as webhooks


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

# Optional: direct admin system page
@app.get("/admin/system")
def admin_system_page():
    return FileResponse(frontend_dir / "admin-system.html")

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

app.include_router(public_apply.router)
app.include_router(system_admin.router)
app.include_router(admin_ai.router)
app.include_router(admin_dashboard.router)
app.include_router(member_dashboard.router)
app.include_router(member_payments.router)

app.include_router(webhooks.router)

# =====================================================
# Startup bootstrap
# =====================================================
@app.on_event("startup")
def bootstrap_admin_user() -> None:
    db = SessionLocal()
    try:
        ensure_admin_user(db)
    finally:
        db.close()
