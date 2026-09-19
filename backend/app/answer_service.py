import json
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from .gemini_client import GeminiClient, GoogleGeminiClient
from .models import CandidateAnswer, Evaluation, InterviewQuestion, InterviewSession
from .schemas import GeminiEvaluationResponse


class AnswerEvaluator(Protocol):
    def evaluate(
        self,
        session: InterviewSession,
        answer: CandidateAnswer,
    ) -> Evaluation:
        ...


class GeminiAnswerEvaluator:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client

    def evaluate(
        self,
        session: InterviewSession,
        answer: CandidateAnswer,
    ) -> Evaluation:
        question = next(
            (item for item in session.questions if item.id == answer.question_id),
            None,
        )
        if question is None:
            raise EvaluationGenerationError("Answer references an unknown question")

        client = self.client or GoogleGeminiClient()
        try:
            result = parse_and_validate_evaluation(
                client.generate(build_evaluation_prompt(session, question, answer))
            )
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as first_error:
            correction_prompt = build_evaluation_correction_prompt(
                session, question, answer, first_error
            )
            try:
                result = parse_and_validate_evaluation(client.generate(correction_prompt))
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as second_error:
                raise EvaluationGenerationError(
                    "Gemini returned invalid evaluation JSON after one correction retry"
                ) from second_error

        return Evaluation(
            score=result.score,
            strengths=result.strengths,
            weaknesses=result.weaknesses,
            feedback=result.feedback,
            recommended_difficulty=result.recommended_difficulty,
            recommended_topics=[result.recommended_topic] if result.recommended_topic else [],
        )


class EvaluationGenerationError(RuntimeError):
    pass


def parse_and_validate_evaluation(raw_response: str) -> GeminiEvaluationResponse:
    if not isinstance(raw_response, str):
        raise TypeError("Gemini response must be text")
    return GeminiEvaluationResponse.model_validate_json(raw_response)


def build_evaluation_prompt(
    session: InterviewSession,
    question: InterviewQuestion,
    answer: CandidateAnswer,
) -> str:
    return (
        "You are a professional Quantumaze interviewer evaluating one answer.\n"
        "Return ONLY valid JSON with exactly these keys: score, strengths, weaknesses, feedback, "
        "recommended_topic, recommended_difficulty.\n"
        "The score must be a numeric integer directly on the 0-100 scale.\n"
        "0 means completely incorrect or no meaningful answer.\n"
        "100 means exceptionally correct, complete, and well-reasoned.\n"
        "NEVER use a 0-10 scale. NEVER return a percentage outside 0-100.\n"
        "Evaluate technical correctness, understanding, reasoning, relevance, completeness, "
        "practical application, and clarity. Do not let grammar or answer length dominate. "
        "A concise technically correct answer can receive a high score.\n"
        f"Candidate profile and experience: {session.candidate_profile.model_dump_json()}\n"
        f"Current round: {session.current_round.value}\n"
        f"Current difficulty: {session.current_difficulty.value}\n"
        f"Question: {question.text}\n"
        f"Candidate answer: {answer.text}\n"
        f"Previous questions: {[item.model_dump() for item in session.questions]}\n"
        f"Previous answers: {[item.model_dump() for item in session.answers]}\n"
        f"Previous evaluations: {[item.model_dump() for item in session.evaluations]}\n"
        f"Relevant round history: {[item.model_dump() for item in session.round_history]}\n"
    )


def build_evaluation_correction_prompt(
    session: InterviewSession,
    question: InterviewQuestion,
    answer: CandidateAnswer,
    error: Exception,
) -> str:
    return (
        build_evaluation_prompt(session, question, answer)
        + "The previous response was malformed or invalid. Return exactly one valid JSON object "
        + f"with the required keys. Validation error: {error}"
    )


def answer_for_question(session: InterviewSession, question_id: UUID) -> CandidateAnswer | None:
    return next(
        (answer for answer in session.answers if answer.question_id == question_id),
        None,
    )