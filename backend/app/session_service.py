from uuid import UUID

from .models import CandidateProfile, Difficulty, InterviewSession
from .round_state_machine import start_session


def create_session(
    candidate_id: UUID,
    candidate_profile: CandidateProfile | None = None,
    initial_difficulty: Difficulty = Difficulty.MEDIUM,
    current_stage: str = "candidate_background",
    target_role: str | None = None,
) -> InterviewSession:
    profile = candidate_profile or CandidateProfile()
    if target_role:
        try:
            profile.target_role = target_role
        except AttributeError:
            pass

    session = InterviewSession(
        candidate_id=candidate_id,
        candidate_profile=profile,
        current_stage=current_stage,
        current_difficulty=initial_difficulty,
        difficulty_progression=[initial_difficulty],
    )
    return start_session(session)