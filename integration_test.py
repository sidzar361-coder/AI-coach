"""Opt-in Gemini smoke test; run directly only when API quota is available."""

import os

from ai_engine import (
    create_interview_session,
    generate_final_report,
    get_next_question,
    run_interview_turn,
)


def main():
    if not os.getenv("GEMINI_API_KEY"):
        print("Skipped: GEMINI_API_KEY is not configured.")
        return

    session = create_interview_session(
        role="Software Engineer",
        experience="Beginner",
        interview_type="Technical",
        difficulty="medium",
        stage="Technical Screening",
    )

    try:
        question = get_next_question(session)
        result = run_interview_turn(
            session,
            question,
            "A queue is FIFO: items are added at the rear and removed from the front. It is useful for scheduling.",
        )
    except Exception as error:
        message = str(error).lower()
        if "429" in message or "quota" in message or "resource exhausted" in message:
            print(f"Gemini quota error: {error}")
            return
        raise

    print("Question:", question)
    print("Evaluation:", result)
    print("Report:", generate_final_report(session))


if __name__ == "__main__":
    main()
