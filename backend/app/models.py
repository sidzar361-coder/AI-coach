from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SessionStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RoundStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RoundNumber(int, Enum):
    BACKGROUND = 1
    PROJECT_DEEP_DIVE = 2
    TECHNICAL_KNOWLEDGE = 3
    PROBLEM_SOLVING = 4
    FINAL_EVALUATION = 5


class BackgroundField(str, Enum):
    CGPA = "cgpa"
    PROJECTS = "projects"
    PROJECT_ROLES = "project_roles"
    TECHNOLOGIES = "technologies"
    EXPERIENCE = "experience"


class QuestionType(str, Enum):
    BACKGROUND = "background"
    PROJECT_DEEP_DIVE = "project_deep_dive"
    TECHNICAL = "technical"
    CODING = "coding"
    DSA = "dsa"
    DEBUGGING = "debugging"
    PRACTICAL_REASONING = "practical_reasoning"


class ProjectProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    role: str = Field(min_length=1)
    technologies: list[str] = Field(min_length=1)


class ExperienceProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    years: float = Field(ge=0)
    summary: str = Field(min_length=1)


class CandidateProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cgpa: Optional[float] = Field(default=None, ge=0, le=10)
    projects: list[ProjectProfile] = Field(default_factory=list)
    experience: Optional[ExperienceProfile] = None

    def completed_background_fields(self) -> set[BackgroundField]:
        fields: set[BackgroundField] = set()

        if self.cgpa is not None:
            fields.add(BackgroundField.CGPA)

        if self.projects:
            fields.add(BackgroundField.PROJECTS)

            if all(project.role for project in self.projects):
                fields.add(BackgroundField.PROJECT_ROLES)

            if all(project.technologies for project in self.projects):
                fields.add(BackgroundField.TECHNOLOGIES)

        if self.experience is not None:
            fields.add(BackgroundField.EXPERIENCE)

        return fields


class ProfileFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: BackgroundField
    value: str = Field(min_length=1)
    source_question_id: Optional[UUID] = None
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class InterviewQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    round_number: RoundNumber
    text: str = Field(min_length=1)
    question_type: QuestionType
    topic: Optional[str] = None
    difficulty: Difficulty
    context_references: list[str] = Field(default_factory=list)
    answered: bool = False
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CandidateAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    question_id: UUID
    round_number: RoundNumber
    text: str = Field(min_length=1)
    evaluation_id: Optional[UUID] = None
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class Evaluation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    score: float = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    feedback: str = ""
    recommended_difficulty: Optional[Difficulty] = None
    recommended_topics: list[str] = Field(default_factory=list)


class RoundState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_number: RoundNumber
    status: RoundStatus = RoundStatus.NOT_STARTED
    question_ids: list[UUID] = Field(default_factory=list)
    answer_ids: list[UUID] = Field(default_factory=list)
    completed_background_fields: set[BackgroundField] = Field(default_factory=set)
    required_topics: set[str] = Field(default_factory=set)
    covered_topics: set[str] = Field(default_factory=set)
    score: Optional[float] = Field(default=None, ge=0, le=100)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class FinalReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_profile: CandidateProfile
    round_scores: dict[str, Optional[float]] = Field(default_factory=dict)
    overall_score: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    recommended_topics: list[str] = Field(default_factory=list)
    difficulty_progression: list[Difficulty] = Field(default_factory=list)
    round_performance: list[dict[str, object]] = Field(default_factory=list)
    question_performance: list[dict[str, object]] = Field(default_factory=list)


class InterviewSession(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    candidate_id: UUID

    status: SessionStatus = SessionStatus.IN_PROGRESS

    current_round: RoundNumber = RoundNumber.BACKGROUND
    current_stage: str = "candidate_background"
    current_difficulty: Difficulty = Difficulty.MEDIUM

    candidate_profile: CandidateProfile = Field(
        default_factory=CandidateProfile
    )

    profile_facts: list[ProfileFact] = Field(default_factory=list)

    round_history: list[RoundState] = Field(
        default_factory=lambda: [
            RoundState(round_number=round_number)
            for round_number in RoundNumber
        ]
    )

    questions: list[InterviewQuestion] = Field(default_factory=list)
    answers: list[CandidateAnswer] = Field(default_factory=list)
    evaluations: list[Evaluation] = Field(default_factory=list)

    recommended_topics: list[str] = Field(default_factory=list)

    difficulty_progression: list[Difficulty] = Field(
        default_factory=list
    )

    final_report: Optional[FinalReport] = None

    round_scores: dict[str, Optional[float]] = Field(
        default_factory=lambda: {
            str(round_number.value): None
            for round_number in RoundNumber
        }
    )

    version: int = 0

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def round_state(self, round_number: RoundNumber) -> RoundState:
        return next(
            state
            for state in self.round_history
            if state.round_number == round_number
        )

    def touch(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)