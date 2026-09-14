# Quantumaze Backend

FastAPI adapter for the existing Quantumaze AI Engine. Sessions are stored in memory for this MVP and are lost when the server stops.

## Install

From the project root:

```powershell
python -m pip install -r backend/requirements.txt
```

The AI Engine's existing Gemini dependency and `GEMINI_API_KEY` configuration are managed separately.

## Start

From the project root:

```powershell
uvicorn backend.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive API documentation is available at `http://localhost:8000/docs`.

## Endpoints

### Create a session

`POST /session`

Request:

```json
{
  "role": "Software Engineer",
  "experience": "Beginner",
  "interview_type": "Technical",
  "difficulty": "medium",
  "stage": "Technical Screening"
}
```

Response:

```json
{
  "session_id": "generated-uuid",
  "session": {
    "role": "Software Engineer",
    "experience": "Beginner",
    "interview_type": "Technical",
    "difficulty": "medium",
    "stage": "Technical Screening",
    "previous_questions": [],
    "previous_topics": [],
    "answers": [],
    "evaluations": [],
    "question_answers": []
  }
}
```

### Generate a question

`GET /session/{session_id}/question`

Response:

```json
{
  "question": "Describe how you would design ..."
}
```

### Submit an answer

`POST /session/{session_id}/answer`

Request:

```json
{
  "question": "Describe how you would design ...",
  "answer": "I would start by ..."
}
```

Response:

```json
{
  "score": 78,
  "strengths": ["Relevant reasoning"],
  "weaknesses": ["Needs more detail"],
  "feedback": "Add a concrete example.",
  "next_difficulty": "medium",
  "recommended_topic": "System design"
}
```

### Get the final report

`GET /session/{session_id}/report`

Returns the structured report from `generate_final_report(session)`.

Unknown session IDs return HTTP 404. Invalid request bodies return HTTP 422.

## CORS

The API allows local development origins on `localhost`, including ports `3000` and `5173`.
