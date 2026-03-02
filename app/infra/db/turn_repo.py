from app.domain.models.turn import InterviewTurn
from app.infra.db.models import InterviewTurnORM


class TurnRepository:

    def __init__(self, db_session):
        self.db = db_session

    def add(self, turn: InterviewTurn):
        orm = InterviewTurnORM(
            id=str(turn.id),
            session_id=str(turn.session_id),
            turn_index=turn.turn_index,
            question_id=turn.question_id,
            question_text=turn.question_text,
            answer_transcript=turn.answer_transcript,
            idempotency_key=getattr(turn, "idempotency_key", None),
            created_at=turn.created_at,
        )
        self.db.add(orm)

    def exists_by_idempotency_key(self, session_id, idempotency_key):
        if not idempotency_key:
            return False
        return (
            self.db.query(InterviewTurnORM)
            .filter_by(session_id=str(session_id), idempotency_key=idempotency_key)
            .first()
            is not None
        )

    def get_history(self, session_id):
        rows = (
            self.db.query(InterviewTurnORM)
            .filter_by(session_id=str(session_id))
            .order_by(InterviewTurnORM.turn_index)
            .all()
        )

        return rows
