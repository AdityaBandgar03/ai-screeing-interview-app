from enum import Enum


class SessionStatus(str, Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
