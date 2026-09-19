import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.answer_service import (
    EvaluationGenerationError,
    GeminiAnswerEvaluator,
    parse_and_validate_evaluation,
)
from app.models import (
    CandidateAnswer,
    CandidateProfile,
    Difficulty,
    ExperienceProfile,
    InterviewQuestion,
    ProjectProfile,
    QuestionType,
    RoundNumber,
)
from app.session_service import create_session


class FakeGeminiClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return self.responses.pop(0)


def make_answer_context():
    session = create_session(
        uuid4(),
        CandidateProfile(
            cgpa=8.5,
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
    question = InterviewQuestion(
        round_number=RoundNumber.BACKGROUND,
        text="What did you build?",
        question_type=QuestionType.BACKGROUND,
        difficulty=Difficulty.MEDIUM,
    )
    answer = CandidateAnswer(
        question_id=question.id,
        round_number=RoundNumber.BACKGROUND,
        text="I built the API layer.",
    )
    session.questions.append(question)
    session.answers.append(answer)
    return session, answer


class EvaluationTests(unittest.TestCase):
    valid = '{"score":88,"strengths":["Correct"],"weaknesses":[],"feedback":"Good answer","recommended_topic":"APIs","recommended_difficulty":"medium"}'

    def test_score_85_is_accepted_on_the_0_to_100_scale(self):
        result = parse_and_validate_evaluation(
            self.valid.replace('"score":88', '"score":85')
        )
        self.assertEqual(result.score, 85)

    def test_valid_evaluation_is_parsed(self):
        result = parse_and_validate_evaluation(self.valid)
        self.assertEqual(result.score, 88)
        self.assertEqual(result.recommended_topic, "APIs")

    def test_score_outside_range_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_and_validate_evaluation(
                self.valid.replace('"score":88', '"score":101')
            )
        with self.assertRaises(ValidationError):
            parse_and_validate_evaluation(
                self.valid.replace('"score":88', '"score":-1')
            )

    def test_non_integer_score_is_rejected(self):
        with self.assertRaises(ValidationError):
            parse_and_validate_evaluation(
                self.valid.replace('"score":88', '"score":85.5')
            )

    def test_malformed_json_retries_exactly_once(self):
        session, answer = make_answer_context()
        client = FakeGeminiClient(["not json", self.valid])
        evaluation = GeminiAnswerEvaluator(client).evaluate(session, answer)
        self.assertEqual(evaluation.score, 88)
        self.assertEqual(len(client.prompts), 2)
        self.assertIn("previous response was malformed", client.prompts[1])

    def test_invalid_schema_retries_and_uses_corrected_result(self):
        session, answer = make_answer_context()
        client = FakeGeminiClient(['{"score":88}', self.valid])
        evaluation = GeminiAnswerEvaluator(client).evaluate(session, answer)
        self.assertEqual(evaluation.recommended_topics, ["APIs"])
        self.assertEqual(len(client.prompts), 2)

    def test_second_failure_returns_controlled_error(self):
        session, answer = make_answer_context()
        client = FakeGeminiClient(["bad", "still bad"])
        with self.assertRaises(EvaluationGenerationError):
            GeminiAnswerEvaluator(client).evaluate(session, answer)
        self.assertEqual(len(client.prompts), 2)

    def test_prompt_contains_profile_round_difficulty_and_history(self):
        session, answer = make_answer_context()
        client = FakeGeminiClient([self.valid])
        GeminiAnswerEvaluator(client).evaluate(session, answer)
        prompt = client.prompts[0]
        self.assertIn("Candidate profile and experience", prompt)
        self.assertIn("Current round: 1", prompt)
        self.assertIn("Current difficulty: medium", prompt)
        self.assertIn("Relevant round history", prompt)
        self.assertIn("numeric integer directly on the 0-100 scale", prompt)
        self.assertIn("NEVER use a 0-10 scale", prompt)
        self.assertIn("0 means completely incorrect", prompt)
        self.assertIn("100 means exceptionally correct", prompt)


if __name__ == "__main__":
    unittest.main()
