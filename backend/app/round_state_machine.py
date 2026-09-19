from datetime import datetime, timezone
from uuid import UUID

from .models import (
    BackgroundField,
    CandidateAnswer,
    Difficulty,
    Evaluation,
    InterviewQuestion,
    InterviewSession,
    RoundNumber,
    RoundStatus,
    SessionStatus,
)


REQUIRED_BACKGROUND_FIELDS = frozenset(BackgroundField)

QUESTIONS_PER_ROUND = 7
ADAPTIVE_ROUNDS = frozenset(
    {
        RoundNumber.PROJECT_DEEP_DIVE,
        RoundNumber.TECHNICAL_KNOWLEDGE,
        RoundNumber.PROBLEM_SOLVING,
    }
)

ROUND_STAGES = {
    RoundNumber.BACKGROUND: "candidate_background",
    RoundNumber.PROJECT_DEEP_DIVE: "project_deep_dive",
    RoundNumber.TECHNICAL_KNOWLEDGE: "technical_knowledge",
    RoundNumber.PROBLEM_SOLVING: "problem_solving",
    RoundNumber.FINAL_EVALUATION: "final_evaluation",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_session(session: InterviewSession) -> InterviewSession:
    if session.status != SessionStatus.IN_PROGRESS:
        raise ValueError("Only an in-progress session can be started")
    if session.current_round != RoundNumber.BACKGROUND:
        raise ValueError("A new session must start at Round 1")

    state = session.round_state(RoundNumber.BACKGROUND)
    if state.status == RoundStatus.NOT_STARTED:
        state.status = RoundStatus.IN_PROGRESS
        state.started_at = _now()
        session.touch()
    return session


def record_profile_field(
    session: InterviewSession,
    field: BackgroundField,
) -> InterviewSession:
    if session.current_round != RoundNumber.BACKGROUND:
        raise ValueError("Profile facts can only be recorded in Round 1")

    state = session.round_state(RoundNumber.BACKGROUND)
    state.completed_background_fields.add(field)
    if state.status == RoundStatus.NOT_STARTED:
        state.status = RoundStatus.IN_PROGRESS
        state.started_at = _now()
    session.touch()
    return session


def add_question(
    session: InterviewSession,
    question: InterviewQuestion,
) -> InterviewSession:
    if question.round_number != session.current_round:
        raise ValueError("Question round does not match the current session round")

    state = session.round_state(session.current_round)
    if state.status == RoundStatus.NOT_STARTED:
        state.status = RoundStatus.IN_PROGRESS
        state.started_at = _now()
    session.questions.append(question)
    state.question_ids.append(question.id)
    if question.topic:
        state.covered_topics.add(question.topic)
    session.touch()
    return session


def record_answer(
    session: InterviewSession,
    answer: CandidateAnswer,
) -> InterviewSession:
    if answer.round_number != session.current_round:
        raise ValueError("Answer round does not match the current session round")
    if answer.question_id not in {
        question.id for question in session.questions
        if question.round_number == session.current_round
    }:
        raise ValueError("Answer references an unknown question")
    if any(existing.question_id == answer.question_id for existing in session.answers):
        raise ValueError("This question has already been answered")

    state = session.round_state(session.current_round)
    state.answer_ids.append(answer.id)
    session.answers.append(answer)
    question = next(item for item in session.questions if item.id == answer.question_id)
    question.answered = True
    session.touch()
    return session


def record_evaluation(
    session: InterviewSession,
    answer_id: UUID,
    evaluation: Evaluation,
) -> InterviewSession:
    answer = next((item for item in session.answers if item.id == answer_id), None)
    if answer is None:
        raise ValueError("Evaluation references an unknown answer")
    if answer.evaluation_id is not None:
        raise ValueError("This answer has already been evaluated")

    answer.evaluation_id = evaluation.id
    session.evaluations.append(evaluation)
    session.recommended_topics = list(
        dict.fromkeys(session.recommended_topics + evaluation.recommended_topics)
    )
    session.current_difficulty = difficulty_for_score(
        evaluation.score,
        session.current_difficulty,
    )
    session.difficulty_progression.append(session.current_difficulty)
    session.touch()
    return session


def is_round_complete(session: InterviewSession) -> bool:
    state = session.round_state(session.current_round)

    if session.current_round != RoundNumber.FINAL_EVALUATION:
        evaluated_count = sum(
            1
            for answer in session.answers
            if answer.round_number == session.current_round
            and answer.evaluation_id is not None
        )
        return evaluated_count >= QUESTIONS_PER_ROUND

    return False


def _round_score(session: InterviewSession, round_number: RoundNumber) -> float | None:
    scores = [
        evaluation.score
        for answer in session.answers
        if answer.round_number == round_number
        for evaluation in session.evaluations
        if evaluation.id == answer.evaluation_id
    ]
    return round(sum(scores) / len(scores), 2) if scores else None


def complete_current_round(session: InterviewSession) -> RoundNumber | None:
    if not is_round_complete(session):
        raise ValueError("Current round requirements are not complete")

    completed_round = session.current_round
    completed_state = session.round_state(completed_round)
    completed_state.status = RoundStatus.COMPLETED
    completed_state.completed_at = _now()
    score = _round_score(session, completed_round)
    completed_state.score = score
    session.round_scores[str(completed_round.value)] = score

    if completed_round == RoundNumber.PROBLEM_SOLVING:
        session.current_round = RoundNumber.FINAL_EVALUATION
        session.current_stage = ROUND_STAGES[RoundNumber.FINAL_EVALUATION]
        session.round_state(RoundNumber.FINAL_EVALUATION).status = RoundStatus.IN_PROGRESS
        session.round_state(RoundNumber.FINAL_EVALUATION).started_at = _now()
    elif completed_round != RoundNumber.FINAL_EVALUATION:
        next_round = RoundNumber(completed_round.value + 1)
        session.current_round = next_round
        session.current_stage = ROUND_STAGES[next_round]
        next_state = session.round_state(next_round)
        next_state.status = RoundStatus.IN_PROGRESS
        next_state.started_at = _now()

    session.touch()
    return session.current_round


def complete_final_evaluation(session: InterviewSession, score: float | None = None) -> InterviewSession:
    if session.current_round != RoundNumber.FINAL_EVALUATION:
        raise ValueError("Final evaluation is not the current round")

    state = session.round_state(RoundNumber.FINAL_EVALUATION)
    state.status = RoundStatus.COMPLETED
    state.completed_at = _now()
    state.score = score
    session.round_scores[str(RoundNumber.FINAL_EVALUATION.value)] = score
    session.status = SessionStatus.COMPLETED
    session.touch()
    return session


def difficulty_for_score(score: float, current: Difficulty) -> Difficulty:
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100")
    if score >= 80:
        return {
            Difficulty.EASY: Difficulty.MEDIUM,
            Difficulty.MEDIUM: Difficulty.HARD,
            Difficulty.HARD: Difficulty.HARD,
        }[current]
    if score < 50:
        return {
            Difficulty.EASY: Difficulty.EASY,
            Difficulty.MEDIUM: Difficulty.EASY,
            Difficulty.HARD: Difficulty.MEDIUM,
        }[current]
    return current
