import unittest
from unittest.mock import patch

from adaptive_engine import determine_next_difficulty
from ai_engine import create_interview_session, generate_final_report
from schemas import validate_evaluation, validate_report


class EngineTests(unittest.TestCase):
    def test_difficulty_adaptation(self):
        self.assertEqual(determine_next_difficulty(80, "easy"), "medium")
        self.assertEqual(determine_next_difficulty(79, "medium"), "medium")
        self.assertEqual(determine_next_difficulty(49, "medium"), "easy")
        self.assertEqual(determine_next_difficulty(95, "hard"), "hard")

    def test_empty_session_report(self):
        session = create_interview_session(
            "Software Engineer", "Beginner", "Technical", "medium", "Screening"
        )
        report = generate_final_report(session)
        self.assertEqual(report["overall_score"], 0)
        self.assertEqual(report["question_performance"], [])
        validate_report(report)

    def test_evaluation_structure_validation(self):
        evaluation = validate_evaluation({
            "score": 72,
            "strengths": ["Correct explanation"],
            "weaknesses": [],
            "feedback": "Add a practical example.",
            "recommended_difficulty": "medium",
            "recommended_topic": "Caching",
        })
        self.assertEqual(evaluation["score"], 72)
        self.assertEqual(evaluation["recommended_topic"], "Caching")

    def test_report_structure(self):
        report = {
            "overall_score": 72,
            "strengths": ["Clear reasoning"],
            "weaknesses": [],
            "recommendations": ["Practice caching"],
            "question_performance": [
                {"question": "Why cache?", "score": 72, "feedback": "Good."}
            ],
        }
        self.assertIs(validate_report(report), report)

    @patch("ai_engine.evaluate_answer")
    def test_process_candidate_answer_updates_session(self, evaluate):
        from ai_engine import process_candidate_answer

        evaluate.return_value = {
            "score": 85,
            "strengths": ["Correct reasoning"],
            "weaknesses": [],
            "feedback": "Good answer.",
            "recommended_difficulty": "hard",
            "recommended_topic": "Concurrency",
        }
        session = create_interview_session(
            "Software Engineer", "Intermediate", "Technical", "medium", "Screening"
        )

        result = process_candidate_answer(session, "Explain a lock.", "It prevents conflicting writes.")

        self.assertEqual(result["score"], 85)
        self.assertEqual(result["next_difficulty"], "hard")
        self.assertEqual(session["previous_topics"], ["Concurrency"])
        self.assertEqual(len(session["question_answers"]), 1)


if __name__ == "__main__":
    unittest.main()
