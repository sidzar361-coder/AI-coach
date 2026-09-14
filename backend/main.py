from typing import Any, Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ai_engine import (
    create_interview_session,
    generate_final_report,
    get_next_question,
    process_candidate_answer,
)


Difficulty = Literal["easy", "medium", "hard"]


class SessionRequest(BaseModel):
    role: str = Field(..., min_length=1)
    experience: str = Field(..., min_length=1)
    interview_type: str = Field(..., min_length=1)
    difficulty: Difficulty
    stage: str = Field(..., min_length=1)


class AnswerRequest(BaseModel):
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class SessionInfo(BaseModel):
    role: str
    experience: str
    interview_type: str
    difficulty: Difficulty
    stage: str
    previous_questions: list[str]
    previous_topics: list[str]
    answers: list[str]
    evaluations: list[dict[str, Any]]
    question_answers: list[dict[str, str]]


class SessionResponse(BaseModel):
    session_id: str
    session: SessionInfo


app = FastAPI(title="Quantumaze AI Interview Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


sessions = {}


def get_session_or_404(session_id: str):
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return session


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/session", response_model=SessionResponse, status_code=201)
def create_session(request: SessionRequest):
    session_id = str(uuid4())
    session = create_interview_session(
        role=request.role,
        experience=request.experience,
        interview_type=request.interview_type,
        difficulty=request.difficulty,
        stage=request.stage,
    )
    sessions[session_id] = session
    return {"session_id": session_id, "session": session}


@app.get("/session/{session_id}/question")
def next_question(session_id: str):
    session = get_session_or_404(session_id)
    try:
        question = get_next_question(session)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Question generation failed: {error}") from error
    return {"question": question}


@app.post("/session/{session_id}/answer")
def submit_answer(session_id: str, request: AnswerRequest):
    session = get_session_or_404(session_id)
    try:
        return process_candidate_answer(session, request.question, request.answer)
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Answer evaluation failed: {error}") from error


@app.get("/session/{session_id}/report")
def final_report(session_id: str):
    session = get_session_or_404(session_id)
    return generate_final_report(session)
