import app.core.config  # noqa: F401 - load .env and config first

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.core.logging import setup_logging
from app.infra.db.database import create_tables
from app.api.routes import sessions, turns


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    create_tables()
    yield


app = FastAPI(title="AI Screening Interview API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(turns.router, prefix="/api/sessions", tags=["turns"])

_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
_index_html = _frontend_dir / "index.html"


@app.get("/")
def serve_frontend():
    """Serve the interview frontend."""
    if _index_html.is_file():
        return FileResponse(_index_html)
    return {"message": "Frontend not found. Create frontend/index.html."}
