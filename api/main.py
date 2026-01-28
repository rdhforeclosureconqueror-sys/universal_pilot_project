from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
