class InterviewError(Exception):
    """Base for interview domain errors."""
    pass


class SessionNotFound(InterviewError):
    """Raised when a session id does not exist."""
    pass


class InvalidSessionState(InterviewError):
    """Raised when an action is not allowed in the current session state."""
    pass


class DuplicateTurnSubmission(InterviewError):
    """Raised when the same idempotency key is used twice for a turn."""
    pass
