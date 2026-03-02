from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_engine
from app.core.logging import get_logger
from app.domain.services.interview_engine import InterviewEngine
from app.domain.exceptions import (
    SessionNotFound,
    InvalidSessionState,
    DuplicateTurnSubmission,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/{session_id}/turns/complete-with-audio")
async def complete_turn_with_audio(
    session_id: UUID,
    audio: UploadFile = File(..., description="Audio file for speech-to-text"),
    idempotency_key: str | None = None,
    engine: InterviewEngine = Depends(get_engine),
):
    """Complete one interview turn by uploading audio; backend runs Whisper STT and stores transcript."""
    logger.info("complete_turn_with_audio requested", extra={"session_id": str(session_id)})
    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
        result = engine.complete_turn(
            session_id=session_id,
            answer_audio=audio_bytes,
            answer_text=None,
            idempotency_key=idempotency_key,
        )
        logger.info(
            "turn completed (audio)",
            extra={"session_id": str(session_id), "finished": result.get("finished", False)},
        )
        return result
    except SessionNotFound:
        raise HTTPException(status_code=404, detail="Session not found")
    except InvalidSessionState as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateTurnSubmission:
        raise HTTPException(status_code=409, detail="Duplicate turn submission")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{session_id}/turns/complete")
def complete_turn(
    session_id: UUID,
    body: dict,
    engine: InterviewEngine = Depends(get_engine),
):
    """Complete one interview turn. Body: { \"answer_text\": \"...\" } or { \"answer_text\", \"idempotency_key\" }."""
    logger.info("complete_turn requested", extra={"session_id": str(session_id)})
    answer_text = body.get("answer_text") or ""
    idempotency_key = body.get("idempotency_key")
    try:
        result = engine.complete_turn(
            session_id=session_id,
            answer_text=answer_text or None,
            idempotency_key=idempotency_key,
        )
        finished = result.get("finished", False)
        logger.info("turn completed", extra={"session_id": str(session_id), "finished": finished})
        return result
    except SessionNotFound:
        logger.warning("complete_turn: session not found", extra={"session_id": str(session_id)})
        raise HTTPException(status_code=404, detail="Session not found")
    except InvalidSessionState as e:
        logger.warning("complete_turn: invalid state", extra={"session_id": str(session_id), "detail": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateTurnSubmission:
        logger.warning("complete_turn: duplicate submission", extra={"session_id": str(session_id)})
        raise HTTPException(status_code=409, detail="Duplicate turn submission")
    except ValueError as e:
        logger.warning("complete_turn: validation error", extra={"session_id": str(session_id), "detail": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("complete_turn failed: %s", e)
        raise
