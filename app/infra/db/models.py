from sqlalchemy import Column, String, Integer, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()


def _uuid_str():
    return str(uuid.uuid4())


class InterviewSessionORM(Base):
    __tablename__ = "interview_sessions"

    id = Column(String(36), primary_key=True, default=_uuid_str)
    question_set = Column(JSON, nullable=False)
    current_question_index = Column(Integer, default=0)
    status = Column(String(32), default="IN_PROGRESS")
    finished_at = Column(DateTime, nullable=True)
    full_transcript = Column(JSON, nullable=True)  # list of {"question_text", "answer_transcript"}
    video_blob_path = Column(String(512), nullable=True)
    job_description = Column(String(5000), nullable=True)
    resume = Column(String(8000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class InterviewTurnORM(Base):
    __tablename__ = "interview_turns"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False)
    turn_index = Column(Integer, nullable=False)
    question_id = Column(String(64), nullable=False)
    question_text = Column(String(2000), nullable=False)
    answer_transcript = Column(String(4000), nullable=False)
    idempotency_key = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
