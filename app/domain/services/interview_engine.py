import threading
from typing import Optional, Tuple
from uuid import UUID

from app.core.logging import get_logger
from app.domain.models.session import InterviewSession
from app.domain.models.turn import InterviewTurn
from app.domain.enums import SessionStatus
from app.domain.exceptions import (
    SessionNotFound,
    InvalidSessionState,
    DuplicateTurnSubmission,
)

logger = get_logger(__name__)


class InterviewEngine:
    """
    Core orchestration engine for interview lifecycle.
    Stateless. All state lives in DB.
    """

    def __init__(
        self,
        session_repo,
        turn_repo,
        llm_provider,
        tts_provider,
        stt_provider,
        unit_of_work,
        audio_storage_service
    ):
        self.session_repo = session_repo
        self.turn_repo = turn_repo
        self.llm = llm_provider
        self.tts = tts_provider
        self.stt = stt_provider
        self.uow = unit_of_work
        self.audio_storage_service = audio_storage_service

    def _upload_audio_to_blob_background(
        self, audio_url: str, session_id: str, question_index: int
    ) -> None:
        """Run blob upload in a background thread (fire-and-forget)."""
        def _run():
            try:
                self.audio_storage_service.upload_from_url(
                    audio_url=audio_url,
                    session_id=session_id,
                    question_index=question_index,
                )
                logger.info(
                    "background blob upload completed",
                    extra={"session_id": session_id, "question_index": question_index},
                )
            except Exception as e:
                logger.warning(
                    "background blob upload failed: %s",
                    e,
                    extra={"session_id": session_id, "question_index": question_index},
                )

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    # ============================================================
    # SESSION CREATION
    # ============================================================

    def create_session(self, jd_text: str, resume_text: str) -> InterviewSession:
        """
        1. Generate question set via LLM
        2. Persist session
        3. Return session with first question ready
        """
        logger.info("create_session: generating question set")
        llm_result = self.llm.generate_question_set(
            job_description=jd_text,
            resume=resume_text,
        )
        question_set = llm_result.get("questions", [{"id": "Q1", "text": "Hi, nice to meet you. Can you introduce yourself?"}])

        session = InterviewSession.create(
            question_set=question_set,
            status=SessionStatus.IN_PROGRESS,
            job_description=jd_text,
            resume=resume_text,
        )

        with self.uow:
            self.session_repo.add(session)
        logger.info("create_session: session persisted", extra={"session_id": str(session.id)})

        # --------------------------------------------------------
        # Generate voice for the first question
        audio_artifact = self.tts.synthesize(session.current_question_text)

        # Return Murf URL for immediate playback; upload to blob in background
        self._upload_audio_to_blob_background(
            audio_url=audio_artifact.url,
            session_id=str(session.id),
            question_index=0,
        )
        return {
            "session_id": str(session.id),
            "question": session.current_question_text,
            "status": session.status,
            "audio_url": audio_artifact.url,
            "mime_type": audio_artifact.mime_type,
        }


    # ============================================================
    # COMPLETE TURN
    # ============================================================

    def complete_turn(
        self,
        session_id: UUID,
        answer_audio: Optional[bytes] = None,
        answer_text: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Handles one interview turn:
        - Validates session
        - Transcribes answer (if audio)
        - Saves turn
        - Advances question sequentially
        - Generates TTS for next question (if any)
        Returns (next_question_text, audio_url). (None, None) when interview finished.
    """
        logger.info("complete_turn: processing", extra={"session_id": str(session_id)})
        with self.uow:
            session = self.session_repo.get(session_id)
            if not session:
                raise SessionNotFound()

            if session.status != SessionStatus.IN_PROGRESS:
                raise InvalidSessionState(
                    f"Cannot complete turn in state {session.status}"
                )

            # Prevent duplicate submissions
            if idempotency_key and self.turn_repo.exists_by_idempotency_key(
                session_id, idempotency_key
            ):
                raise DuplicateTurnSubmission()

            # ----------------------------------------------------
            # Step 1: Resolve transcript
            # ----------------------------------------------------
            transcript = answer_text

            if answer_audio:
                transcript = self.stt.transcribe(answer_audio)

            if not transcript:
                raise ValueError("Transcript cannot be empty")

            # ----------------------------------------------------
            # Step 2: Persist Turn
            # ----------------------------------------------------
            turn = InterviewTurn.create(
                session_id=session.id,
                turn_index=session.current_question_index,
                question_id=session.current_question_id,
                question_text=session.current_question_text,
                answer_transcript=transcript,
                idempotency_key=idempotency_key,
            )

            self.turn_repo.add(turn)

            # Store this Q&A in the session's full transcript
            self.session_repo.append_to_transcript(
                session_id, session.current_question_text, transcript
            )

            # ----------------------------------------------------
            # Step 3: LLM decides next step (follow_up / ask_new / end)
            # ----------------------------------------------------
            qa_history = self.session_repo.get_transcript(session_id)
            question_count = len(session.question_set)
            result = self.llm.get_next_prompt(
                job_description=session.job_description,
                resume=session.resume,
                full_transcript=qa_history,
                question_count=question_count,
            )
            decision = result.get("decision", "end")
            next_question = result.get("question")
            closing_message = result.get("closing_message")

            if decision == "end" or not next_question:
                session.mark_finished()
            elif decision == "follow_up":
                session.set_follow_up(next_question)
            else:
                session.add_new_question(next_question)

            # ----------------------------------------------------
            # Step 4: Update session state
            # ----------------------------------------------------
            self.session_repo.update(session)

        logger.info(
            "complete_turn: turn persisted",
            extra={"session_id": str(session_id), "decision": decision, "finished": decision == "end"},
        )

        # --------------------------------------------------------
        # Step 5: Generate TTS (outside transaction)
        # --------------------------------------------------------
        if decision == "end":
            return {
                "question": None,
                "audio_url": None,
                "finished": True,
                "closing_message": closing_message,
            }

        audio_artifact = self.tts.synthesize(next_question)
        utterance_index = len(qa_history)
        # Return Murf URL for immediate playback; upload to blob in background
        self._upload_audio_to_blob_background(
            audio_url=audio_artifact.url,
            session_id=str(session.id),
            question_index=utterance_index,
        )
        return {
            "question": next_question,
            "audio_url": audio_artifact.url,
            "mime_type": audio_artifact.mime_type,
            "finished": False,
        }

    # ============================================================
    # EVALUATION
    # ============================================================

    def evaluate_session(self, session_id: UUID) -> dict:
        """
        Evaluate a finished session using JD, resume, and full transcript.
        Returns evaluation dict (recommendation, summary, strengths, concerns, role_fit_score, suggested_next_step).
        """
        with self.uow:
            session = self.session_repo.get(session_id)
            if not session:
                raise SessionNotFound()
            if session.status != "FINISHED":
                raise InvalidSessionState("Evaluation only allowed for finished sessions")
            transcript = self.session_repo.get_transcript(session_id)
            if not transcript:
                raise InvalidSessionState("No transcript available for evaluation")

        lines = []
        for i, pair in enumerate(transcript, 1):
            lines.append(f"Q{i}: {pair.get('question_text', '')}")
            lines.append(f"A{i}: {pair.get('answer_transcript', '')}")
        transcript_text = "\n".join(lines)

        logger.info("evaluate_session: running LLM evaluation", extra={"session_id": str(session_id)})
        return self.llm.evaluate_interview(
            job_description=session.job_description,
            resume=session.resume,
            transcript_text=transcript_text,
        )
