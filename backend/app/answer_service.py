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
    
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    return GeminiEvaluationResponse.model_validate_json(cleaned)


def build_evaluation_prompt(
    session: InterviewSession,
    question: InterviewQuestion,
    answer: CandidateAnswer,
) -> str:
    # Compile a history of previously asked question types/topics in this session to prevent repetition
    asked_topics = [q.text[:40] for q in session.questions if q.id != question.id]
    history_context = f"Previously covered question concepts in this session: {asked_topics}" if asked_topics else "This is the first question."

    return (
        "You are an expert interview coach.\n"
        "Do NOT provide technical solution corrections or math answers.\n"
        "Instead, evaluate ONLY the candidate's speaking style/delivery, and identify the core topic/type of the question just answered.\n"
        "Return ONLY valid JSON with exactly these keys: score, strengths, weaknesses, feedback, "
        "recommended_topic, recommended_difficulty.\n"
        "- score: Integer from 0 to 100 based on speaking delivery.\n"
        "- strengths: Short bullet points on speaking delivery strengths.\n"
        "- weaknesses: Short bullet points on communication skills to improve.\n"
        "- feedback: A brief statement on delivery.\n"
        f"- recommended_topic: A short phrase describing the specific question type/concept just covered (e.g., 'Covered: Object-Oriented Programming concepts') so future questions can avoid repeating this type.\n"
        "- recommended_difficulty: MEDIUM\n"
        f"{history_context}\n"
        f"Current Question Text: {question.text}\n"
        f"Candidate Answer: {answer.text}\n"
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