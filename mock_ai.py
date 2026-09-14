def mock_evaluate_answer(question, answer):
    """
    Development/testing mock only; this is not the AI engine.
    """

    answer_length = len(answer.split())

    if answer_length >= 40:
        return {
            "score": 85,
            "strengths": [
                "Answer demonstrates a reasonable understanding of the topic.",
                "Candidate provides supporting explanation."
            ],
            "weaknesses": [
                "The response could be more structured."
            ],
            "feedback": (
                "Good response. Strengthen it further by providing "
                "a precise practical example."
            ),
            "recommended_difficulty": "hard",
            "recommended_topic": "Advanced Data Structures"
        }

    elif answer_length >= 20:
        return {
            "score": 65,
            "strengths": [
                "Answer addresses the main concept."
            ],
            "weaknesses": [
                "The explanation lacks depth."
            ],
            "feedback": (
                "The response is relevant. Add deeper reasoning "
                "and a practical example."
            ),
            "recommended_difficulty": "medium",
            "recommended_topic": "Data Structures"
        }

    else:
        return {
            "score": 35,
            "strengths": [
                "Candidate attempted to answer the question."
            ],
            "weaknesses": [
                "The answer lacks sufficient explanation."
            ],
            "feedback": (
                "Provide a clearer explanation of the concept "
                "and include an example."
            ),
            "recommended_difficulty": "easy",
            "recommended_topic": "Data Structures Fundamentals"
        }