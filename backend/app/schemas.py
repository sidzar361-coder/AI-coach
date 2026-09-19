from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    CandidateAnswer,
    CandidateProfile,
    BackgroundField,
    Difficulty,
    Evaluation,
    FinalReport,
    InterviewQuestion,
    InterviewSession,
    ProfileFact,
    RoundNumber,
    RoundState,
)


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: UUID
    candidate_profile: CandidateProfile = Field(default_factory=CandidateProfile)
    current_stage: str = Field(default="candidate_background", min_length=1)
    initial_difficulty: Difficulty = Difficulty.MEDIUM


class CreateSessionResponse(BaseModel):
    session_id: UUID
    session: InterviewSession


class UpdateProfileRequest(CandidateProfile):
    pass


class SubmitAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    question: Optional[str] = None
    answer: str = Field(min_length=1)
    session_version: int = Field(ge=0)


class SubmitProfileFactRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    field: BackgroundField
    value: str = Field(min_length=1)
    session_version: int = Field(ge=0)


class EvaluationResponse(BaseModel):
    evaluation: Evaluation
    next_difficulty: Difficulty
    round_completed: bool
    next_round: Optional[RoundNumber] = None


class SessionStateResponse(BaseModel):
    session_id: UUID
    status: str
    current_round: RoundNumber
    current_stage: str
    current_difficulty: Difficulty
    candidate_profile: CandidateProfile
    profile_facts: list[ProfileFact]
    round_history: list[RoundState]
    previous_questions: list[InterviewQuestion]
    previous_answers: list[CandidateAnswer]
    evaluations: list[Evaluation]
    recommended_topics: list[str]
    difficulty_progression: list[Difficulty]
    round_scores: dict[str, Optional[float]]
    final_report: Optional[FinalReport]
    version: int


class RoundTransitionResponse(BaseModel):
    session_id: UUID
    completed_round: RoundNumber
    next_round: Optional[RoundNumber]
    current_difficulty: Difficulty
    round_score: Optional[float]
    session_version: int


class QuestionResponse(BaseModel):
    question: InterviewQuestion


class GeminiQuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    round: RoundNumber
    difficulty: Difficulty


class GeminiEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    feedback: str
    recommended_topic: str
    recommended_difficulty: Difficulty


class AnswerSubmissionResponse(BaseModel):
    answer: CandidateAnswer
    evaluation: Evaluation
    evaluation_pending: bool = False
    session: SessionStateResponse


class ReportResponse(BaseModel):
    session_id: UUID
    available: bool
    current_round: RoundNumber
    message: str
    report: Optional[FinalReport] = None
