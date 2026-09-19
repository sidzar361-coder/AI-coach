from uuid import UUID

from .models import CandidateProfile, Difficulty, InterviewSession
from .round_state_machine import start_session


def create_session(
    candidate_id: UUID,
    candidate_profile: CandidateProfile | None = None,
    initial_difficulty: Difficulty = Difficulty.MEDIUM,
    current_stage: str = "candidate_background",
) -> InterviewSession:
    session = InterviewSession(
        candidate_id=candidate_id,
        candidate_profile=candidate_profile or CandidateProfile(),
        current_stage=current_stage,
        current_difficulty=initial_difficulty,
        difficulty_progression=[initial_difficulty],
    )
    return start_session(session)