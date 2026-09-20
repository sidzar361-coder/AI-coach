from uuid import UUID

from .models import CandidateAnswer, InterviewQuestion, InterviewSession, RoundNumber
from .answer_service import AnswerEvaluator
from .question_service import QuestionGenerator
from .repository import SessionRepository
from .report_service import generate_final_report
from .round_state_machine import (
    complete_current_round,
    complete_final_evaluation,
    is_round_complete,
    record_answer,
    record_evaluation,
)
from .schemas import CreateSessionRequest, SubmitAnswerRequest
from .session_service import create_session


class SessionNotFoundError(Exception):
    pass


class QuestionNotFoundError(Exception):
    pass


class SessionApiService:
    def __init__(self, repository: SessionRepository) -> None:
        self.repository = repository

    def create(self, request: CreateSessionRequest) -> InterviewSession:
        session = create_session(
            candidate_id=request.candidate_id,
            candidate_profile=request.candidate_profile,
            current_stage=request.current_stage,
            initial_difficulty=request.initial_difficulty,
            target_round=getattr(request, 'target_round', 1),
        )
        return self.repository.create(session)

    def get(self, session_id: UUID) -> InterviewSession:
        session = self.repository.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        return session

    def submit_answer(self, session_id: UUID, request: SubmitAnswerRequest) -> InterviewSession:
        session = self.get(session_id)
        if request.session_version != session.version:
            raise ValueError("Session version is stale")

        question = next(
            (item for item in session.questions if item.id == request.question_id),
            None,
        )
        if question is None:
            raise QuestionNotFoundError(request.question_id)
        if request.question is not None and request.question != question.text:
            raise ValueError("Question text does not match the stored question")

        answer = CandidateAnswer(
            question_id=question.id,
            round_number=session.current_round,
            text=request.answer,
        )
        record_answer(session, answer)
        return self.repository.save(session)

    def submit_and_evaluate_answer(
        self,
        session_id: UUID,
        request: SubmitAnswerRequest,
        evaluator: AnswerEvaluator,
    ) -> tuple[InterviewSession, CandidateAnswer]:
        session = self.get(session_id)
        if request.session_version != session.version:
            raise ValueError("Session version is stale")

        question = next(
            (item for item in session.questions if item.id == request.question_id),
            None,
        )
        if question is None:
            raise QuestionNotFoundError(request.question_id)
        if request.question is not None and request.question != question.text:
            raise ValueError("Question text does not match the stored question")

        answer = CandidateAnswer(
            question_id=question.id,
            round_number=session.current_round,
            text=request.answer,
        )
        record_answer(session, answer)
        evaluation = evaluator.evaluate(session, answer)
        record_evaluation(session, answer.id, evaluation)
        if is_round_complete(session):
            complete_current_round(session)
            if session.current_round == RoundNumber.FINAL_EVALUATION:
                session.final_report = generate_final_report(session)
                complete_final_evaluation(session, session.final_report.overall_score)
                session.final_report = generate_final_report(session)
        return self.repository.save(session), answer

    def generate_question(
        self,
        session_id: UUID,
        generator: QuestionGenerator,
    ) -> tuple[InterviewSession, InterviewQuestion]:
        session = self.get(session_id)
        question = generator.generate(session)
        session.questions.append(question)
        session.round_state(session.current_round).question_ids.append(question.id)
        session.touch()
        return self.repository.save(session), question