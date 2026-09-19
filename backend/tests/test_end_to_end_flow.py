import asyncio
import json
import re
import unittest
from uuid import uuid4
from unittest.mock import patch

import httpx

from app.answer_service import GeminiAnswerEvaluator
from app.main import app, repository
from app.question_service import GeminiQuestionGenerator


class ScenarioGeminiClient:
    def __init__(self):
        self.question_prompts = []
        self.evaluation_prompts = []

    def generate(self, prompt):
        if "Return ONLY raw JSON with exactly these keys: question" in prompt:
            self.question_prompts.append(prompt)
            round_number = int(re.search(r"Expected round: (\d+)", prompt).group(1))
            topics = {
                1: "background",
                2: "project architecture",
                3: "FastAPI",
                4: "debugging",
            }
            return json.dumps(
                {
                    "question": f"Round {round_number} question",
                    "topic": topics[round_number],
                    "round": round_number,
                    "difficulty": re.search(
                        r"expected difficulty: (\w+)", prompt
                    ).group(1),
                }
            )

        self.evaluation_prompts.append(prompt)
        round_number = int(re.search(r"Current round: (\d+)", prompt).group(1))
        scores = {1: 90, 2: 70, 3: 80, 4: 60}
        return json.dumps(
            {
                "score": scores[round_number],
                "strengths": [f"Round {round_number} strength"],
                "weaknesses": [f"Round {round_number} weakness"],
                "feedback": "Clear and relevant answer.",
                "recommended_topic": f"round-{round_number}-topic",
                "recommended_difficulty": "easy",
            }
        )


class EndToEndFlowTests(unittest.TestCase):
    def setUp(self):
        repository._sessions.clear()
        self.client = ScenarioGeminiClient()
        self.question_generator = GeminiQuestionGenerator(self.client)
        self.evaluator = GeminiAnswerEvaluator(self.client)

    def request(self, method, path, **kwargs):
        async def send():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.request(method, path, **kwargs)

        return asyncio.run(send())

    def test_complete_round_one_to_round_five_flow(self):
        with patch("app.main.question_generator", self.question_generator), patch(
            "app.main.answer_evaluator", self.evaluator
        ):
            created = self.request(
                "POST",
                "/session",
                json={
                    "candidate_id": str(uuid4()),
                    "candidate_profile": {
                        "cgpa": 8.7,
                        "projects": [
                            {
                                "name": "Quantumaze",
                                "description": "Adaptive interview platform",
                                "role": "Backend developer",
                                "technologies": ["Python", "FastAPI", "PostgreSQL"],
                            }
                        ],
                        "experience": {"years": 1, "summary": "Backend internship"},
                    },
                    "initial_difficulty": "easy",
                },
            )
            self.assertEqual(created.status_code, 201)
            session_id = created.json()["session_id"]

            self._answer_current_question(session_id, expected_round=1)
            state = self.request("GET", f"/session/{session_id}").json()
            self.assertEqual(state["current_round"], 2)
            self.assertEqual(state["current_difficulty"], "medium")

            self._answer_current_question(session_id, expected_round=2)
            question_prompt = self.client.question_prompts[-1]
            self.assertIn("Quantumaze", question_prompt)
            self.assertIn("Previous answers", question_prompt)
            self._answer_current_question(session_id, expected_round=2)
            self._answer_current_question(session_id, expected_round=2)

            self.assertEqual(
                self.request("GET", f"/session/{session_id}").json()["current_round"],
                3,
            )
            self._answer_current_question(session_id, expected_round=3)
            self._answer_current_question(session_id, expected_round=3)
            self._answer_current_question(session_id, expected_round=3)
            self._answer_current_question(session_id, expected_round=4)
            self._answer_current_question(session_id, expected_round=4)
            self._answer_current_question(session_id, expected_round=4)

            final_state = self.request("GET", f"/session/{session_id}").json()
            self.assertEqual(final_state["current_round"], 5)
            self.assertEqual(final_state["status"], "completed")
            self.assertEqual(final_state["current_difficulty"], "hard")
            self.assertEqual(len(final_state["previous_questions"]), 10)
            self.assertEqual(len(final_state["previous_answers"]), 10)
            self.assertEqual(len(final_state["evaluations"]), 10)

            report_response = self.request("GET", f"/session/{session_id}/report")
            self.assertEqual(report_response.status_code, 200)
            report = report_response.json()["report"]
            self.assertTrue(report_response.json()["available"])
            self.assertIn("candidate_profile", report)
            self.assertEqual(report["candidate_profile"]["cgpa"], 8.7)
            self.assertEqual(set(report["round_scores"]) , {"1", "2", "3", "4", "5"})
            self.assertIsNotNone(report["overall_score"])
            self.assertTrue(report["strengths"])
            self.assertTrue(report["weaknesses"])
            self.assertTrue(report["recommendations"])
            self.assertTrue(report["recommended_topics"])
            self.assertTrue(report["difficulty_progression"])
            self.assertEqual(len(report["question_performance"]), 10)

            round_five_question = self.request(
                "GET", f"/session/{session_id}/question"
            )
            self.assertEqual(round_five_question.status_code, 502)
            self.assertIn("Round 5", round_five_question.json()["detail"])

    def _answer_current_question(self, session_id, expected_round):
        question_response = self.request("GET", f"/session/{session_id}/question")
        self.assertEqual(question_response.status_code, 200)
        question = question_response.json()["question"]
        self.assertEqual(question["round_number"], expected_round)
        state = self.request("GET", f"/session/{session_id}").json()
        response = self.request(
            "POST",
            f"/session/{session_id}/answer",
            json={
                "question_id": question["id"],
                "answer": f"Realistic answer for round {expected_round}.",
                "session_version": state["version"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("evaluation", response.json())
        self.assertIn("evaluations", response.json()["session"])


if __name__ == "__main__":
    unittest.main()