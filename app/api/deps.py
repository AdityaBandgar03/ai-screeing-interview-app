from fastapi import Depends
from sqlalchemy.orm import Session

from app.core import config
from app.infra.db.database import get_db
from app.infra.db.unit_of_work import UnitOfWork
from app.infra.db.session_repo import SessionRepository
from app.infra.db.turn_repo import TurnRepository
from app.providers.llm.azure_openai import AzureOpenAILLMProvider
from app.providers.tts.murf_speech import MurfTTSProvider
from app.providers.stt.whisper_api import AzureWhisperSTTProvider
from app.providers.blob_storage.blob_client import AudioStorageService
from app.domain.services.interview_engine import InterviewEngine


def get_uow(db: Session = Depends(get_db)):
    return UnitOfWork(db)


def get_session_repo(db: Session = Depends(get_db)):
    return SessionRepository(db)


def get_turn_repo(db: Session = Depends(get_db)):
    return TurnRepository(db)


def get_engine(
    session_repo: SessionRepository = Depends(get_session_repo),
    turn_repo: TurnRepository = Depends(get_turn_repo),
    uow: UnitOfWork = Depends(get_uow),
):
    return create_interview_engine(session_repo=session_repo, turn_repo=turn_repo, uow=uow)


def create_interview_engine(session_repo, turn_repo, uow):
    llm_provider = AzureOpenAILLMProvider(
        endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        deployment_name="gpt-4o",
    )
    tts_provider = MurfTTSProvider(
        api_key=config.MURF_API_KEY,
        voice_id="en-US-terrell",
        audio_format="WAV",
        timeout=120,
    )
    stt_provider = AzureWhisperSTTProvider(
        endpoint=config.AZURE_OPENAI_ENDPOINT,
        api_key=config.AZURE_OPENAI_API_KEY,
        deployment_name="whisper",
    )
    audio_storage_service = AudioStorageService(
        connection_string=config.AZURE_BLOB_CONNECTION_STRING,
        container_name="jayant-container-doc",
    )
    return InterviewEngine(
        session_repo=session_repo,
        turn_repo=turn_repo,
        llm_provider=llm_provider,
        tts_provider=tts_provider,
        stt_provider=stt_provider,
        unit_of_work=uow,
        audio_storage_service=audio_storage_service,
    )
