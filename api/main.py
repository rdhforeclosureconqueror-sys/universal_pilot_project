from pathlib import Path
import os

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from api.routes import ai, auth, bulk_upload, botops, cases, consent, deals, documents, referral, training, imports, properties


app = FastAPI()

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
app.include_router(imports.router)
app.include_router(properties.router)
