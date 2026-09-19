import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.models import (
    CandidateProfile,
    Difficulty,
    ExperienceProfile,
    ProjectProfile,
    RoundNumber,
)
from app.question_service import (
    GeminiQuestionGenerator,
    QuestionGenerationError,
    parse_and_validate,
)
from app.session_service import create_session


class FakeGeminiClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.responses.pop(0)


def make_session(round_number=RoundNumber.BACKGROUND):
    session = create_session(
        uuid4(),
        CandidateProfile(
            cgpa=8.4,
            projects=[
                ProjectProfile(
                    name="Quantumaze",
                    description="Interview platform",
                    role="Backend developer",
                    technologies=["Python", "FastAPI"],
                )
            ],
            experience=ExperienceProfile(years=1, summary="Backend internship"),
        ),
        Difficulty.MEDIUM,
    )
    if round_number != RoundNumber.BACKGROUND:
        session.current_round = round_number
        session.current_stage = {
            RoundNumber.PROJECT_DEEP_DIVE: "project_deep_dive",
            RoundNumber.TECHNICAL_KNOWLEDGE: "technical_knowledge",
            RoundNumber.PROBLEM_SOLVING: "problem_solving",
            RoundNumber.FINAL_EVALUATION: "final_evaluation",
        }[round_number]
    return session


class QuestionGenerationTests(unittest.TestCase):
    valid = '{"question":"Tell me about your project.","topic":"projects","round":1,"difficulty":"medium"}'

    def test_valid_gemini_json_is_parsed_and_validated(self):
        result = parse_and_validate(self.valid)
        self.assertEqual(result.question, "Tell me about your project.")
        self.assertEqual(result.round, RoundNumber.BACKGROUND)

    def test_valid_json_inside_json_markdown_fence_is_parsed(self):
        fenced = f"```json\n{self.valid}\n```"
        result = parse_and_validate(fenced)
        self.assertEqual(result.question, "Tell me about your project.")
        self.assertEqual(result.round, RoundNumber.BACKGROUND)

    def test_genuinely_invalid_json_is_rejected(self):
        with self.assertRaises(Exception):
            parse_and_validate("not json")

    def test_malformed_json_retries_and_returns_corrected_question(self):
        client = FakeGeminiClient([
            "not json",
            self.valid,
        ])
        question = GeminiQuestionGenerator(client).generate(make_session())
        self.assertEqual(question.text, "Tell me about your project.")
        self.assertEqual(len(client.prompts), 2)
        self.assertIn("previous response was invalid", client.prompts[1])

    def test_invalid_schema_retries_exactly_once(self):
        client = FakeGeminiClient([
            '{"question":"Missing fields"}',
            self.valid,
        ])
        question = GeminiQuestionGenerator(client).generate(make_session())
        self.assertEqual(question.topic, "projects")
        self.assertEqual(len(client.prompts), 2)

    def test_second_failure_returns_controlled_error(self):
        client = FakeGeminiClient(["bad", "still bad"])
        with self.assertRaises(QuestionGenerationError):
            GeminiQuestionGenerator(client).generate(make_session())
        self.assertEqual(len(client.prompts), 2)

    def test_round_specific_generation_uses_stage_and_question_type(self):
        cases = [
            (RoundNumber.BACKGROUND, "candidate_background", "background"),
            (RoundNumber.PROJECT_DEEP_DIVE, "project_deep_dive", "project_deep_dive"),
            (RoundNumber.TECHNICAL_KNOWLEDGE, "technical_knowledge", "technical"),
            (RoundNumber.PROBLEM_SOLVING, "problem_solving", "practical_reasoning"),
        ]
        for round_number, stage, question_type in cases:
            response = (
                '{"question":"Question", "topic":"topic", '
                f'"round":{round_number.value}, "difficulty":"medium"}}'
            )
            client = FakeGeminiClient([response])
            session = make_session(round_number)
            question = GeminiQuestionGenerator(client).generate(session)
            self.assertEqual(question.round_number, round_number)
            self.assertEqual(question.question_type.value, question_type)
            self.assertIn(stage, client.prompts[0])
            self.assertIn("Candidate profile", client.prompts[0])
            self.assertIn("Relevant round history", client.prompts[0])

    def test_question_prompt_requires_raw_json_without_fences(self):
        client = FakeGeminiClient([self.valid])
        GeminiQuestionGenerator(client).generate(make_session())
        self.assertIn("ONLY raw JSON", client.prompts[0])
        self.assertIn("Do NOT use Markdown code fences", client.prompts[0])
        self.assertIn("```json fences", client.prompts[0])

    def test_round_five_does_not_generate(self):
        client = FakeGeminiClient([])
        with self.assertRaises(QuestionGenerationError):
            GeminiQuestionGenerator(client).generate(make_session(RoundNumber.FINAL_EVALUATION))
        self.assertEqual(client.prompts, [])


if __name__ == "__main__":
    unittest.main()
