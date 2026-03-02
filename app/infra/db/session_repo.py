import uuid
from app.domain.models.session import InterviewSession
from app.infra.db.models import InterviewSessionORM


class SessionRepository:

    def __init__(self, db_session):
        self.db = db_session

    def add(self, session: InterviewSession):
        orm = InterviewSessionORM(
            id=str(session.id),
            question_set=session.question_set,
            current_question_index=session.current_question_index,
            status=session.status,
            finished_at=session.finished_at,
            job_description=session.job_description,
            resume=session.resume,
        )
        self.db.add(orm)
        self.db.flush()
        return uuid.UUID(orm.id)

    def get(self, session_id):
        sid = str(session_id)
        orm = self.db.query(InterviewSessionORM).get(sid)
        if not orm:
            return None

        session = InterviewSession(
            question_set=orm.question_set,
            current_question_index=orm.current_question_index,
            status=orm.status,
            finished_at=orm.finished_at,
            id=uuid.UUID(orm.id),
            job_description=orm.job_description or "",
            resume=orm.resume or "",
        )
        return session

    def update(self, session: InterviewSession):
        orm = self.db.query(InterviewSessionORM).get(str(session.id))
        if not orm:
            raise ValueError("Session not found for update")

        orm.question_set = session.question_set
        orm.current_question_index = session.current_question_index
        orm.status = session.status
        orm.finished_at = session.finished_at

    def append_to_transcript(self, session_id, question_text: str, answer_transcript: str):
        """Append one Q&A pair to the session's full conversation transcript."""
        orm = self.db.query(InterviewSessionORM).get(str(session_id))
        if not orm:
            return
        current = list(orm.full_transcript) if orm.full_transcript else []
        current.append({
            "question_text": question_text,
            "answer_transcript": answer_transcript,
        })
        orm.full_transcript = current

    def get_transcript(self, session_id):
        """Return the full conversation transcript as a list of {question_text, answer_transcript}."""
        orm = self.db.query(InterviewSessionORM).get(str(session_id))
        if not orm or not orm.full_transcript:
            return []
        return list(orm.full_transcript)

    def set_video_blob_path(self, session_id, blob_path: str):
        """Store the video blob path for the session (after client upload)."""
        orm = self.db.query(InterviewSessionORM).get(str(session_id))
        if not orm:
            return
        orm.video_blob_path = blob_path
