from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional


class InterviewTurn:
    def __init__(
        self,
        id: UUID,
        session_id: UUID,
        turn_index: int,
        question_id: str,
        question_text: str,
        answer_transcript: str,
        created_at: Optional[datetime] = None,
        idempotency_key: Optional[str] = None,
    ):
        self.id = id
        self.session_id = session_id
        self.turn_index = turn_index
        self.question_id = question_id
        self.question_text = question_text
        self.answer_transcript = answer_transcript
        self.created_at = created_at or datetime.utcnow()
        self.idempotency_key = idempotency_key

    @classmethod
    def create(
        cls,
        session_id: UUID,
        question_id: str,
        question_text: str,
        answer_transcript: str,
        turn_index: Optional[int] = None,
        idempotency_key: Optional[str] = None,
    ) -> "InterviewTurn":
        return cls(
            id=uuid4(),
            session_id=session_id,
            turn_index=turn_index if turn_index is not None else 0,
            question_id=question_id,
            question_text=question_text,
            answer_transcript=answer_transcript,
            idempotency_key=idempotency_key,
        )
