from uuid import UUID

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .api_service import (
    QuestionNotFoundError,
    SessionApiService,
    SessionNotFoundError,
)
from .answer_service import EvaluationGenerationError, GeminiAnswerEvaluator
from .models import InterviewSession
from .question_service import GeminiQuestionGenerator, QuestionGenerationError
from .repository import SessionRepository
from .schemas import (
    AnswerSubmissionResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    QuestionResponse,
    ReportResponse,
    SessionStateResponse,
    SubmitAnswerRequest,
)


app = FastAPI(title="Quantumaze AI Interview Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
repository = SessionRepository()
session_service = SessionApiService(repository)
question_generator = GeminiQuestionGenerator()
answer_evaluator = GeminiAnswerEvaluator()


def to_state_response(session: InterviewSession) -> SessionStateResponse:
    return SessionStateResponse(
        session_id=session.id,
        status=session.status.value,
        current_round=session.current_round,
        current_stage=session.current_stage,
        current_difficulty=session.current_difficulty,
        candidate_profile=session.candidate_profile,
        profile_facts=session.profile_facts,
        round_history=session.round_history,
        previous_questions=session.questions,
        previous_answers=session.answers,
        evaluations=session.evaluations,
        recommended_topics=session.recommended_topics,
        difficulty_progression=session.difficulty_progression,
        round_scores=session.round_scores,
        final_report=session.final_report,
        version=session.version,
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/session", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session_route(request: CreateSessionRequest) -> CreateSessionResponse:
    session = session_service.create(request)
    return CreateSessionResponse(session_id=session.id, session=session)


@app.get("/session/{session_id}", response_model=SessionStateResponse)
def get_session_route(session_id: UUID) -> SessionStateResponse:
    try:
        return to_state_response(session_service.get(session_id))
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Interview session not found") from error


@app.get("/session/{session_id}/question", response_model=QuestionResponse)
def get_question_route(session_id: UUID) -> QuestionResponse:
    try:
        _, question = session_service.generate_question(session_id, question_generator)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Interview session not found") from error
    except (QuestionGenerationError, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return QuestionResponse(question=question)


@app.post("/session/{session_id}/answer", response_model=AnswerSubmissionResponse)
def submit_answer_route(
    session_id: UUID,
    request: SubmitAnswerRequest,
) -> AnswerSubmissionResponse:
    try:
        session, answer = session_service.submit_and_evaluate_answer(
            session_id,
            request,
            answer_evaluator,
        )
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Interview session not found") from error
    except QuestionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Question not found") from error
    except (EvaluationGenerationError, RuntimeError) as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    evaluation = next(
        item for item in session.evaluations
        if item.id == answer.evaluation_id
    )
    return AnswerSubmissionResponse(
        answer=answer,
        evaluation=evaluation,
        session=to_state_response(session),
    )


@app.get("/session/{session_id}/report", response_model=ReportResponse)
def get_report_route(session_id: UUID) -> ReportResponse:
    try:
        session = session_service.get(session_id)
    except SessionNotFoundError as error:
        raise HTTPException(status_code=404, detail="Interview session not found") from error

    available = session.final_report is not None
    return ReportResponse(
        session_id=session.id,
        available=available,
        current_round=session.current_round,
        message=(
            "Final report is available"
            if available
            else "Final report is not yet available; interview is incomplete"
        ),
        report=session.final_report,
    )