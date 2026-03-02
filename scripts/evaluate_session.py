"""
CLI script to evaluate a candidate for a finished interview session.
Fetches JD, resume, and conversation transcript from the DB, then runs LLM evaluation.

Usage:
    python -m scripts.evaluate_session --session-id <SESSION_UUID>
    python -m scripts.evaluate_session -s <SESSION_UUID>

Example:
    python -m scripts.evaluate_session --session-id 52bdd6d7-94c8-4f3e-b197-cdcb7629ea4c
"""
import argparse
import json
import sys
from uuid import UUID

# Load config and env before other app imports
import app.core.config  # noqa: F401

from app.infra.db.database import SessionLocal
from app.infra.db.session_repo import SessionRepository
from app.infra.db.turn_repo import TurnRepository
from app.infra.db.unit_of_work import UnitOfWork
from app.api.deps import create_interview_engine
from app.domain.exceptions import SessionNotFound, InvalidSessionState


def get_session_id(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid session ID (must be UUID): {value}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a candidate for a finished interview session using JD, resume, and transcript."
    )
    parser.add_argument(
        "-s", "--session-id",
        required=True,
        type=get_session_id,
        help="Session UUID to evaluate (e.g. 52bdd6d7-94c8-4f3e-b197-cdcb7629ea4c)",
    )
    parser.add_argument(
        "--show-inputs",
        action="store_true",
        help="Print JD, resume snippet, and transcript before running evaluation",
    )
    args = parser.parse_args()
    session_id = args.session_id

    db = SessionLocal()
    try:
        session_repo = SessionRepository(db)
        turn_repo = TurnRepository(db)
        uow = UnitOfWork(db)
        engine = create_interview_engine(
            session_repo=session_repo,
            turn_repo=turn_repo,
            uow=uow,
        )

        session = session_repo.get(session_id)
        if not session:
            print("Error: Session not found.", file=sys.stderr)
            sys.exit(1)
        if session.status != "FINISHED":
            print("Error: Session is not finished. Only finished sessions can be evaluated.", file=sys.stderr)
            sys.exit(1)

        transcript = session_repo.get_transcript(session_id)
        if not transcript:
            print("Error: No transcript available for this session.", file=sys.stderr)
            sys.exit(1)

        if args.show_inputs:
            print("--- Job Description (first 500 chars) ---")
            print((session.job_description or "")[:500])
            if (session.job_description or "").strip():
                print("...")
            print("\n--- Resume (first 500 chars) ---")
            print((session.resume or "")[:500])
            if (session.resume or "").strip():
                print("...")
            print("\n--- Conversation Transcript ---")
            for i, pair in enumerate(transcript, 1):
                print(f"Q{i}: {pair.get('question_text', '')}")
                print(f"A{i}: {pair.get('answer_transcript', '')}")
            print("\n--- Running evaluation ---\n")

        result = engine.evaluate_session(session_id)
        print(json.dumps(result, indent=2))
    except SessionNotFound:
        print("Error: Session not found.", file=sys.stderr)
        sys.exit(1)
    except InvalidSessionState as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
