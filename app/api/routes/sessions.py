from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_engine, get_session_repo
from app.core.docx_utils import extract_text_from_docx
from app.core.logging import get_logger
from app.domain.services.interview_engine import InterviewEngine
from app.domain.exceptions import SessionNotFound, InvalidSessionState
from app.infra.db.database import get_db
from app.infra.db.session_repo import SessionRepository

router = APIRouter()
logger = get_logger(__name__)


@router.post("/{session_id}/evaluate")
def evaluate_session(
    session_id: UUID,
    engine: InterviewEngine = Depends(get_engine),
):
    """Evaluate a finished interview. Returns recommendation, summary, strengths, concerns, role_fit_score, suggested_next_step."""
    try:
        result = engine.evaluate_session(session_id)
        logger.info("evaluation completed", extra={"session_id": str(session_id)})
        return result
    except SessionNotFound:
        raise HTTPException(status_code=404, detail="Session not found")
    except InvalidSessionState as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/video/upload-url")
def get_video_upload_url(
    session_id: UUID,
    engine: InterviewEngine = Depends(get_engine),
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """Return a SAS URL for the client to upload the interview video. Session must exist."""
    if not session_repo.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        upload_url, blob_path = engine.audio_storage_service.generate_video_upload_sas(
            str(session_id)
        )
        return {"upload_url": upload_url, "blob_path": blob_path}
    except Exception as e:
        logger.exception("get_video_upload_url failed: %s", e)
        raise


@router.post("/{session_id}/video/finalize")
def finalize_video(
    session_id: UUID,
    body: dict,
    session_repo: SessionRepository = Depends(get_session_repo),
    db=Depends(get_db),
):
    """Save the video blob path after client has uploaded. Body: { \"blob_path\": \"...\" }."""
    if not session_repo.get(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    blob_path = body.get("blob_path")
    if not blob_path:
        raise HTTPException(status_code=400, detail="blob_path required")
    session_repo.set_video_blob_path(session_id, blob_path)
    db.commit()
    return {"ok": True}


@router.post("", status_code=201)
async def create_session(
    job_description: UploadFile = File(..., description="Job description .docx file"),
    resume: UploadFile = File(..., description="Candidate resume .docx file"),
    engine: InterviewEngine = Depends(get_engine),
):
    """Create a new interview session. Upload job_description.docx and resume.docx."""
    logger.info("create_session requested")
    if not job_description.filename or not job_description.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="job_description must be a .docx file")
    if not resume.filename or not resume.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="resume must be a .docx file")
    try:
        jd_bytes = await job_description.read()
        resume_bytes = await resume.read()
        jd_text = extract_text_from_docx(jd_bytes)
        resume_text = extract_text_from_docx(resume_bytes)
        if not jd_text.strip():
            raise HTTPException(
                status_code=400,
                detail="job_description .docx could not be read or is empty",
            )
        if not resume_text.strip():
            raise HTTPException(
                status_code=400,
                detail="resume .docx could not be read or is empty",
            )
        result = engine.create_session(jd_text=jd_text, resume_text=resume_text)
        logger.info("session created", extra={"session_id": result.get("session_id")})
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("create_session failed: %s", e)
        raise
