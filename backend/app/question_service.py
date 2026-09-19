import json
from typing import Protocol

from pydantic import ValidationError

from .gemini_client import GeminiClient, GoogleGeminiClient
from .models import InterviewQuestion, InterviewSession, QuestionType, RoundNumber
from .schemas import GeminiQuestionResponse


class QuestionGenerationError(RuntimeError):
    pass


class QuestionGenerator(Protocol):
    def generate(self, session: InterviewSession) -> InterviewQuestion:
        ...


QUESTION_TYPES = {
    RoundNumber.BACKGROUND: QuestionType.PRACTICAL_REASONING,
    RoundNumber.PROJECT_DEEP_DIVE: QuestionType.PROJECT_DEEP_DIVE,
    RoundNumber.TECHNICAL_KNOWLEDGE: QuestionType.TECHNICAL,
    RoundNumber.PROBLEM_SOLVING: QuestionType.PRACTICAL_REASONING,
}


class GeminiQuestionGenerator:
    def __init__(self, client: GeminiClient | None = None) -> None:
        self.client = client

    def generate(self, session: InterviewSession) -> InterviewQuestion:
        if session.current_round == RoundNumber.FINAL_EVALUATION:
            raise QuestionGenerationError(
                "Round 5 is reserved for final evaluation and does not generate questions"
            )

        client = self.client or GoogleGeminiClient()
        raw_response = client.generate(build_question_prompt(session))
        try:
            result = parse_and_validate(raw_response)
        except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as first_error:
            correction_prompt = build_correction_prompt(session, raw_response, first_error)
            try:
                result = parse_and_validate(client.generate(correction_prompt))
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as second_error:
                raise QuestionGenerationError(
                    "Gemini returned invalid question JSON after one correction retry"
                ) from second_error

        if result.round != session.current_round:
            raise QuestionGenerationError("Gemini returned a question for the wrong round")
        if result.difficulty != session.current_difficulty:
            raise QuestionGenerationError("Gemini returned a question with the wrong difficulty")

        return InterviewQuestion(
            round_number=result.round,
            text=result.question,
            question_type=QUESTION_TYPES[session.current_round],
            topic=result.topic,
            difficulty=result.difficulty,
            context_references=_context_references(session),
        )


def parse_and_validate(raw_response: str) -> GeminiQuestionResponse:
    if not isinstance(raw_response, str):
        raise TypeError("Gemini response must be text")
    cleaned_response = raw_response.strip()
    if cleaned_response.startswith("```json") and cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[len("```json"):-len("```")].strip()
    return GeminiQuestionResponse.model_validate_json(cleaned_response)


def build_question_prompt(session: InterviewSession) -> str:
    instructions = {
        RoundNumber.BACKGROUND: (
            "This is the Aptitude Round. Ask one aptitude question involving quantitative reasoning, "
            "logical reasoning, verbal reasoning, patterns, percentages, probability, data interpretation, "
            "or problem-solving under time pressure. Do not ask about programming, frameworks, databases, "
            "system design, projects, work experience, or technical implementation."
        ),
        RoundNumber.PROJECT_DEEP_DIVE: (
            "This is the Project and Managerial Round. Ask one question about the candidate's project "
            "decisions, ownership, teamwork, prioritization, leadership, trade-offs, delivery, or project impact. "
            "Use the candidate's actual project history. Do not ask generic coding or database questions."
        ),
        RoundNumber.TECHNICAL_KNOWLEDGE: (
            "This is the Technical Round. Ask one role-specific technical question about programming, "
            "data structures, APIs, databases, networking, cloud, system design, or the technologies in the profile."
        ),
        RoundNumber.PROBLEM_SOLVING: (
            "This is the Problem-Solving and Behavioral Round. Ask one practical scenario, debugging, "
            "decision-making, communication, conflict, adaptability, or structured reasoning question. "
            "Do not repeat a pure technical theory question."
        ),
    }
    return _prompt_header(session, instructions[session.current_round])


def build_correction_prompt(session: InterviewSession, invalid_response: str, error: Exception) -> str:
    return (
        _prompt_header(session)
        + "\nThe previous response was invalid. Return ONLY one valid JSON object. "
        + "Use exactly these keys: question, topic, round, difficulty. "
        + f"Validation error: {error}\nPrevious response:\n{invalid_response}"
    )


def _prompt_header(session: InterviewSession, instruction: str = "") -> str:
    return (
        "You are a professional Quantumaze interviewer conducting a structured interview.\n"
        "Return ONLY raw JSON with exactly these keys: question, topic, round, difficulty.\n"
        "Do NOT use Markdown code fences, ```json fences, or any other triple-backtick wrapper.\n"
        f"Expected round: {session.current_round.value}; expected difficulty: {session.current_difficulty.value}\n"
        f"Current stage: {session.current_stage}\nRound instruction: {instruction}\n"
        f"Candidate profile: {session.candidate_profile.model_dump_json()}\n"
        f"Previous questions: {[question.model_dump() for question in session.questions]}\n"
        f"Previous answers: {[answer.model_dump() for answer in session.answers]}\n"
        f"Evaluations: {[evaluation.model_dump() for evaluation in session.evaluations]}\n"
        f"Recommended topics: {session.recommended_topics}\n"
        f"Relevant round history: {[state.model_dump() for state in session.round_history]}\n"
        "Do not repeat previous questions. Ask exactly one question. "
        "The round instruction is a hard constraint: never mix content from another round."
    )


def _context_references(session: InterviewSession) -> list[str]:
    references = [project.name for project in session.candidate_profile.projects]
    references.extend(
        technology
        for project in session.candidate_profile.projects
        for technology in project.technologies
    )
    return list(dict.fromkeys(references))