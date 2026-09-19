from copy import deepcopy
from uuid import UUID

from .models import InterviewSession


class SessionRepository:
    def __init__(self) -> None:
        self._sessions: dict[UUID, InterviewSession] = {}

    def create(self, session: InterviewSession) -> InterviewSession:
        if session.id in self._sessions:
            raise ValueError("Session already exists")
        self._sessions[session.id] = deepcopy(session)
        return deepcopy(session)

    def get(self, session_id: UUID) -> InterviewSession | None:
        session = self._sessions.get(session_id)
        return deepcopy(session) if session is not None else None

    def save(self, session: InterviewSession) -> InterviewSession:
        if session.id not in self._sessions:
            raise KeyError(session.id)
        self._sessions[session.id] = deepcopy(session)
        return deepcopy(session)