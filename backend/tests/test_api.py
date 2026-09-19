import asyncio
import unittest
from uuid import UUID, uuid4

import httpx

from app.main import app, repository
from app.models import InterviewQuestion, QuestionType
from app.answer_service import GeminiAnswerEvaluator
from app.question_service import GeminiQuestionGenerator
from unittest.mock import patch


class ApiTests(unittest.TestCase):
    def setUp(self):
        repository._sessions.clear()

    def request(self, method, path, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    def create_session(self):
        response = self.request(
            "POST",
            "/session",
            json={
                "candidate_id": str(uuid4()),
                "candidate_profile": {
                    "cgpa": 8.2,
                    "projects": [
                        {
                            "name": "API project",
                            "description": "A backend API",
                            "role": "Developer",
                            "technologies": ["Python", "FastAPI"],
                        }
                    ],
                    "experience": {"years": 1, "summary": "Internship"},
                },
                "initial_difficulty": "easy",
            },
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_create_and_get_session(self):
        created = self.create_session()
        session_id = created["session_id"]

        self.assertEqual(created["session"]["current_round"], 1)
        self.assertEqual(created["session"]["current_difficulty"], "easy")

        response = self.request("GET", f"/session/{session_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["session_id"], session_id)
        self.assertNotIn("GEMINI_API_KEY", response.text)

    def test_unknown_session_returns_404(self):
        session_id = uuid4()
        self.assertEqual(self.request("GET", f"/session/{session_id}").status_code, 404)
        self.assertEqual(
            self.request("GET", f"/session/{session_id}/question").status_code,
            404,
        )
        self.assertEqual(
            self.request("GET", f"/session/{session_id}/report").status_code,
            404,
        )

    def test_question_route_exposes_gemini_configuration_error(self):
        created = self.create_session()
        response = self.request("GET", f"/session/{created['session_id']}/question")
        self.assertEqual(response.status_code, 502)
        self.assertIn("GEMINI_API_KEY", response.json()["detail"])

    def test_question_route_returns_and_persists_validated_question(self):
        created = self.create_session()
        fake_client = type(
            "FakeClient",
            (),
            {"generate": lambda self, prompt: '{"question":"What did you build?","topic":"projects","round":1,"difficulty":"easy"}'},
        )()
        generator = GeminiQuestionGenerator(fake_client)
        with patch("app.main.question_generator", generator):
            response = self.request("GET", f"/session/{created['session_id']}/question")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["question"]["text"], "What did you build?")
        stored = repository.get(UUID(created["session_id"]))
        self.assertEqual(len(stored.questions), 1)

    def test_answer_route_persists_valid_evaluation(self):
        created = self.create_session()
        session_id = UUID(created["session_id"])
        session = repository.get(session_id)
        question = InterviewQuestion(
            round_number=session.current_round,
            text="Tell me about your project.",
            question_type=QuestionType.BACKGROUND,
            difficulty=session.current_difficulty,
        )
        session.questions.append(question)
        session.round_state(session.current_round).question_ids.append(question.id)
        repository.save(session)

        fake_client = type(
            "FakeClient",
            (),
            {"generate": lambda self, prompt: '{"score":88,"strengths":["Correct"],"weaknesses":[],"feedback":"Good answer","recommended_topic":"APIs","recommended_difficulty":"medium"}'},
        )()
        evaluator = GeminiAnswerEvaluator(fake_client)
        with patch("app.main.answer_evaluator", evaluator):
            response = self.request(
                "POST",
                f"/session/{session_id}/answer",
                json={
                    "question_id": str(question.id),
                    "question": question.text,
                    "answer": "I built the API layer.",
                    "session_version": session.version,
                },
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["evaluation_pending"])
        self.assertEqual(body["evaluation"]["score"], 88)
        self.assertEqual(body["session"]["previous_answers"][0]["text"], "I built the API layer.")
        self.assertEqual(body["session"]["evaluations"][0]["score"], 88)

    def test_answer_route_unknown_question_returns_404(self):
        created = self.create_session()
        response = self.request(
            "POST",
            f"/session/{created['session_id']}/answer",
            json={
                "question_id": str(uuid4()),
                "answer": "answer",
                "session_version": 1,
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_answer_route_rejects_invalid_answer(self):
        created = self.create_session()
        response = self.request(
            "POST",
            f"/session/{created['session_id']}/answer",
            json={
                "question_id": str(uuid4()),
                "answer": "",
                "session_version": 1,
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_failed_evaluation_does_not_persist_answer_or_evaluation(self):
        created = self.create_session()
        session_id = UUID(created["session_id"])
        session = repository.get(session_id)
        question = InterviewQuestion(
            round_number=session.current_round,
            text="Tell me about your project.",
            question_type=QuestionType.BACKGROUND,
            difficulty=session.current_difficulty,
        )
        session.questions.append(question)
        session.round_state(session.current_round).question_ids.append(question.id)
        repository.save(session)
        fake_client = type(
            "FakeClient",
            (),
            {"responses": ["bad", "still bad"], "generate": lambda self, prompt: self.responses.pop(0)},
        )()
        with patch("app.main.answer_evaluator", GeminiAnswerEvaluator(fake_client)):
            response = self.request(
                "POST",
                f"/session/{session_id}/answer",
                json={
                    "question_id": str(question.id),
                    "answer": "I built the API layer.",
                    "session_version": session.version,
                },
            )

        self.assertEqual(response.status_code, 502)
        stored = repository.get(session_id)
        self.assertEqual(stored.answers, [])
        self.assertEqual(stored.evaluations, [])

    def test_answer_route_rejects_stale_session_version(self):
        created = self.create_session()
        response = self.request(
            "POST",
            f"/session/{created['session_id']}/answer",
            json={
                "question_id": str(uuid4()),
                "answer": "answer",
                "session_version": 0,
            },
        )
        self.assertEqual(response.status_code, 409)

    def test_incomplete_report_is_explicit(self):
        created = self.create_session()
        response = self.request("GET", f"/session/{created['session_id']}/report")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["available"])
        self.assertIn("not yet available", response.json()["message"])
        self.assertIsNone(response.json()["report"])


if __name__ == "__main__":
    unittest.main()