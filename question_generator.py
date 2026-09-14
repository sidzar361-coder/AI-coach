from config import create_gemini_interaction
from prompts import build_question_prompt



def generate_question(
    role,
    experience,
    interview_type,
    difficulty,
    stage,
    previous_questions=None,
    previous_topics=None
):
    """
    Generates a new interview question using Gemini.

    The model uses previous questions and topics
    to reduce repetition and maintain adaptive
    interview progression.
    """

    previous_questions = previous_questions or []
    previous_topics = previous_topics or []

    prompt = build_question_prompt(
        role, experience, interview_type, difficulty, stage,
        previous_questions, previous_topics
    )

    response = create_gemini_interaction(prompt)

    return response.output_text.strip()