from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    member_dashboard,
    member_payments,
    public_apply,
    system_admin,
)

# ✅ Import all route modules
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
    leads,  # ✅ Newly added auction import route
    workflow,
    partner_api,
)

app = FastAPI()
app.include_router(leads.router)
# ✅ Mount static frontend directory (relative to this file)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


# ✅ Serve the root index.html
@app.get("/")
def read_root():
    return FileResponse(frontend_dir / "index.html")


# ✅ Serve CSS
@app.get("/styles.css")
def read_styles():
    return FileResponse(frontend_dir / "styles.css")


# ✅ Serve JavaScript
@app.get("/app.js")
def read_app_js():
    return FileResponse(frontend_dir / "app.js")


# ✅ Serve dynamic config.js for API base
@app.get("/config.js")
def read_config():
    api_base = os.getenv("VITE_API_BASE_URL", "").strip()
    js = f'window.__API_BASE_URL__ = "{api_base}";'
    return Response(content=js, media_type="application/javascript")


# ✅ Register all routers
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
app.include_router(auction_imports.router)  # ✅ Needed for /auction-imports/*
app.include_router(workflow.router)

app.include_router(partner_api.router)
app.include_router(public_apply.router)
app.include_router(system_admin.router)
app.include_router(member_dashboard.router)
app.include_router(member_payments.router)


@app.get("/admin/system")
def admin_system_page():
    return FileResponse(frontend_dir / "admin-system.html")
