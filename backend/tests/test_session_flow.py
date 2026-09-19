import unittest
from uuid import uuid4

from app.models import (
    BackgroundField,
    CandidateAnswer,
    CandidateProfile,
    Difficulty,
    Evaluation,
    ExperienceProfile,
    InterviewQuestion,
    ProjectProfile,
    QuestionType,
    RoundNumber,
    RoundStatus,
    SessionStatus,
)
from app.round_state_machine import (
    complete_current_round,
    complete_final_evaluation,
    difficulty_for_score,
    is_round_complete,
    record_answer,
    record_evaluation,
    start_session,
    add_question,
)
from app.session_service import create_session


class SessionFlowTests(unittest.TestCase):
    def setUp(self):
        profile = CandidateProfile(
            cgpa=8.6,
            projects=[
                ProjectProfile(
                    name="Expense Tracker",
                    description="Tracks personal spending.",
                    role="Backend developer",
                    technologies=["Python", "FastAPI"],
                )
            ],
            experience=ExperienceProfile(years=1, summary="Backend internship"),
        )
        self.session = create_session(uuid4(), profile, Difficulty.EASY)

    def test_session_starts_in_round_one_with_profile_and_difficulty(self):
        self.assertEqual(self.session.current_round, RoundNumber.BACKGROUND)
        self.assertEqual(self.session.current_difficulty, Difficulty.EASY)
        self.assertEqual(
            self.session.round_state(RoundNumber.BACKGROUND).status,
            RoundStatus.IN_PROGRESS,
        )
        self.assertEqual(self.session.candidate_profile.cgpa, 8.6)

    def test_round_one_waits_for_all_factual_fields(self):
        self.session.candidate_profile = CandidateProfile(cgpa=8.6)
        start_session(self.session)
        self.assertFalse(is_round_complete(self.session))

        self.session.candidate_profile = CandidateProfile(
            cgpa=8.6,
            projects=[
                ProjectProfile(
                    name="Expense Tracker",
                    description="Tracks personal spending.",
                    role="Backend developer",
                    technologies=["Python"],
                )
            ],
            experience=ExperienceProfile(years=1, summary="Backend internship"),
        )
        self.assertTrue(is_round_complete(self.session))
        complete_current_round(self.session)
        self.assertEqual(self.session.current_round, RoundNumber.PROJECT_DEEP_DIVE)

    def test_adaptive_round_transitions_after_three_evaluated_answers(self):
        complete_current_round(self.session)

        for _ in range(3):
            question = InterviewQuestion(
                round_number=RoundNumber.PROJECT_DEEP_DIVE,
                text="Explain your project design.",
                question_type=QuestionType.PROJECT_DEEP_DIVE,
                topic="project architecture",
                difficulty=self.session.current_difficulty,
            )
            add_question(self.session, question)
            answer = CandidateAnswer(
                question_id=question.id,
                round_number=RoundNumber.PROJECT_DEEP_DIVE,
                text="I separated the API and persistence layers.",
            )
            record_answer(self.session, answer)
            record_evaluation(
                self.session,
                answer.id,
                Evaluation(
                    score=85,
                    strengths=["Clear design explanation"],
                    recommended_difficulty=Difficulty.HARD,
                ),
            )

        self.assertTrue(is_round_complete(self.session))
        complete_current_round(self.session)
        self.assertEqual(self.session.current_round, RoundNumber.TECHNICAL_KNOWLEDGE)
        self.assertEqual(self.session.round_scores["2"], 85.0)
        self.assertEqual(self.session.current_difficulty, Difficulty.HARD)

    def test_final_round_marks_session_complete(self):
        complete_current_round(self.session)
        while self.session.current_round != RoundNumber.FINAL_EVALUATION:
            self._complete_current_adaptive_round()

        self.assertEqual(self.session.current_round, RoundNumber.FINAL_EVALUATION)
        complete_final_evaluation(self.session, score=79)
        self.assertEqual(self.session.status, SessionStatus.COMPLETED)
        self.assertEqual(self.session.round_scores["5"], 79.0)

    def _complete_current_adaptive_round(self):
        for _ in range(3):
            question = InterviewQuestion(
                round_number=self.session.current_round,
                text="Solve this interview problem.",
                question_type=QuestionType.TECHNICAL,
                difficulty=self.session.current_difficulty,
            )
            add_question(self.session, question)
            answer = CandidateAnswer(
                question_id=question.id,
                round_number=self.session.current_round,
                text="I would test assumptions and explain the tradeoffs.",
            )
            record_answer(self.session, answer)
            record_evaluation(self.session, answer.id, Evaluation(score=70))

        complete_current_round(self.session)


class DifficultyTests(unittest.TestCase):
    def setUp(self):
        self.session = create_session(
            uuid4(),
            CandidateProfile(
                cgpa=8.6,
                projects=[
                    ProjectProfile(
                        name="Expense Tracker",
                        description="Tracks personal spending.",
                        role="Backend developer",
                        technologies=["Python", "FastAPI"],
                    )
                ],
                experience=ExperienceProfile(years=1, summary="Backend internship"),
            ),
            Difficulty.EASY,
        )

    def test_easy_increases_to_medium(self):
        self.assertEqual(difficulty_for_score(90, Difficulty.EASY), Difficulty.MEDIUM)

    def test_medium_increases_to_hard(self):
        self.assertEqual(difficulty_for_score(80, Difficulty.MEDIUM), Difficulty.HARD)

    def test_hard_remains_hard_on_high_score(self):
        self.assertEqual(difficulty_for_score(90, Difficulty.HARD), Difficulty.HARD)

    def test_hard_decreases_to_medium(self):
        self.assertEqual(difficulty_for_score(49, Difficulty.HARD), Difficulty.MEDIUM)

    def test_medium_decreases_to_easy(self):
        self.assertEqual(difficulty_for_score(40, Difficulty.MEDIUM), Difficulty.EASY)

    def test_easy_remains_easy_on_low_score(self):
        self.assertEqual(difficulty_for_score(40, Difficulty.EASY), Difficulty.EASY)

    def test_medium_is_unchanged_for_middle_score(self):
        self.assertEqual(difficulty_for_score(65, Difficulty.MEDIUM), Difficulty.MEDIUM)

    def test_round_transition_preserves_complete_history(self):
        complete_current_round(self.session)
        original_profile = self.session.candidate_profile.model_copy(deep=True)
        question = InterviewQuestion(
            round_number=RoundNumber.PROJECT_DEEP_DIVE,
            text="Explain the project.",
            question_type=QuestionType.PROJECT_DEEP_DIVE,
            difficulty=self.session.current_difficulty,
        )
        add_question(self.session, question)
        answer = CandidateAnswer(
            question_id=question.id,
            round_number=RoundNumber.PROJECT_DEEP_DIVE,
            text="I built the service.",
        )
        record_answer(self.session, answer)
        record_evaluation(self.session, answer.id, Evaluation(score=80))
        for _ in range(2):
            extra = InterviewQuestion(
                round_number=RoundNumber.PROJECT_DEEP_DIVE,
                text="What tradeoff did you make?",
                question_type=QuestionType.PROJECT_DEEP_DIVE,
                difficulty=self.session.current_difficulty,
            )
            add_question(self.session, extra)
            extra_answer = CandidateAnswer(
                question_id=extra.id,
                round_number=RoundNumber.PROJECT_DEEP_DIVE,
                text="I considered performance and simplicity.",
            )
            record_answer(self.session, extra_answer)
            record_evaluation(self.session, extra_answer.id, Evaluation(score=70))

        complete_current_round(self.session)
        self.assertEqual(self.session.current_round, RoundNumber.TECHNICAL_KNOWLEDGE)
        self.assertEqual(self.session.candidate_profile, original_profile)
        self.assertEqual(len(self.session.questions), 3)
        self.assertEqual(len(self.session.answers), 3)
        self.assertEqual(len(self.session.evaluations), 3)
        self.assertEqual(self.session.round_scores["2"], 73.33)

    def test_round_five_is_final_evaluation_only(self):
        self.session.current_round = RoundNumber.FINAL_EVALUATION
        self.session.current_stage = "final_evaluation"
        with self.assertRaises(ValueError):
            complete_current_round(self.session)
        complete_final_evaluation(self.session, score=75)
        self.assertEqual(self.session.status, SessionStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()
