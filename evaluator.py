import json

from config import create_gemini_interaction
from prompts import build_evaluation_prompt
from schemas import validate_evaluation


def evaluate_answer(
    question,
    answer,
    role="Software Engineer",
    experience="Beginner",
    difficulty="medium"
):

    prompt = build_evaluation_prompt(question, answer, role, experience, difficulty)

    response = create_gemini_interaction(prompt)

    text = response.output_text.strip()

    # Remove Markdown code fences if Gemini adds them
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(line for line in lines if not line.strip().startswith("``")).strip()

    try:
        result = json.loads(text)

    except json.JSONDecodeError:
        raise RuntimeError(
            f"Gemini returned invalid JSON:\n{text}"
        )

    try:
        return validate_evaluation(result)
    except ValueError as error:
        raise RuntimeError(f"Gemini returned an invalid evaluation: {error}") from error