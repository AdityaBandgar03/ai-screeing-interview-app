from typing import Optional, List, Any
from datetime import datetime
import uuid


class InterviewSession:
    def __init__(
        self,
        question_set: list,
        current_question_index: int = 0,
        status: str = "IN_PROGRESS",
        finished_at: Optional[datetime] = None,
        id: Optional[Any] = None,
        job_description: Optional[str] = None,
        resume: Optional[str] = None,
    ):
        self.id = id
        self.question_set = question_set
        self.current_question_index = current_question_index
        self.status = status.value if hasattr(status, "value") else status
        self.finished_at = finished_at
        self.job_description = job_description or ""
        self.resume = resume or ""

        if question_set and 0 <= current_question_index < len(question_set):
            q = question_set[current_question_index]
            self.current_question_id = q["id"]
            self.current_question_text = q["text"]
        else:
            self.current_question_id = None
            self.current_question_text = None

    @classmethod
    def create(
        cls,
        question_set: list,
        status: str = "IN_PROGRESS",
        job_description: str = "",
        resume: str = "",
    ) -> "InterviewSession":
        """Create session with first question and optional JD/resume."""
        status_value = status.value if hasattr(status, "value") else status
        return cls(
            id=uuid.uuid4(),
            question_set=question_set,
            current_question_index=0,
            status=status_value,
            job_description=job_description,
            resume=resume,
        )

    def set_follow_up(self, text: str) -> None:
        """Append follow-up to question_set and set as current (derived from index)."""
        follow_id = (self.current_question_id or "Q1") + "-f"
        self.question_set.append({"id": follow_id, "text": text})
        self.current_question_index = len(self.question_set) - 1
        self.current_question_id = follow_id
        self.current_question_text = text

    def add_new_question(self, text: str) -> None:
        """Append a new main question and set it as current."""
        next_id = f"Q{len(self.question_set) + 1}"
        self.question_set.append({"id": next_id, "text": text})
        self.current_question_index = len(self.question_set) - 1
        self.current_question_id = next_id
        self.current_question_text = text

    def remaining_questions(self) -> List[Any]:
        """Return list of questions not yet asked (after current index)."""
        return self.question_set[self.current_question_index + 1 :]

    def advance_to_next_question(self, question: Any) -> None:
        """
        Set current question from LLM decision.
        question: str (text only) or dict with "id" and "text".
        """
        if isinstance(question, str):
            self.current_question_index += 1
            self.current_question_text = question
            if self.current_question_index < len(self.question_set):
                self.current_question_id = self.question_set[self.current_question_index]["id"]
            else:
                self.current_question_id = None
        else:
            self.current_question_id = question.get("id")
            self.current_question_text = question.get("text", "")
            for i, q in enumerate(self.question_set):
                if q.get("id") == self.current_question_id:
                    self.current_question_index = i
                    return
            self.current_question_index += 1

    def advance_sequentially(self) -> Optional[str]:
        """
        Move to next question in predefined order.
        Returns next question text or None if finished.
        """
        self.current_question_index += 1

        if self.current_question_index >= len(self.question_set):
            return None

        next_q = self.question_set[self.current_question_index]
        self.current_question_id = next_q["id"]
        self.current_question_text = next_q["text"]

        return self.current_question_text

    def mark_finished(self) -> None:
        self.status = "FINISHED"
        self.finished_at = datetime.utcnow()
