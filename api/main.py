from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import ai, auth, bulk_upload, cases, consent, documents, referral, training, imports, properties

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


app.include_router(ai.router)
app.include_router(auth.router)
app.include_router(bulk_upload.router)
app.include_router(cases.router)
app.include_router(consent.router)
app.include_router(documents.router)
app.include_router(referral.router)
app.include_router(training.router)
app.include_router(imports.router)
app.include_router(properties.router)
