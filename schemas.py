VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def validate_evaluation(value):
    """Validate and normalize the evaluator contract."""
    if not isinstance(value, dict):
        raise ValueError("Evaluation must be a JSON object.")

    try:
        score = float(value["score"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Evaluation score must be numeric.") from error

    if not 0 <= score <= 100:
        raise ValueError("Evaluation score must be between 0 and 100.")

    strengths = value.get("strengths", [])
    weaknesses = value.get("weaknesses", [])
    feedback = value.get("feedback", "")
    recommended_difficulty = value.get("recommended_difficulty", "medium")
    recommended_topic = value.get("recommended_topic", "")

    if not isinstance(strengths, list) or not isinstance(weaknesses, list):
        raise ValueError("Strengths and weaknesses must be lists.")
    if not isinstance(feedback, str):
        raise ValueError("Feedback must be a string.")
    if recommended_difficulty not in VALID_DIFFICULTIES:
        raise ValueError("Recommended difficulty is invalid.")
    if not isinstance(recommended_topic, str):
        raise ValueError("Recommended topic must be a string.")

    normalized_score = int(score) if score.is_integer() else score
    return {
        "score": normalized_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "feedback": feedback,
        "recommended_difficulty": recommended_difficulty,
        "recommended_topic": recommended_topic,
    }


def validate_report(value):
    """Validate the public final-report shape."""
    required = {"overall_score", "strengths", "weaknesses", "recommendations", "question_performance"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise ValueError("Report is missing required fields.")
    if not isinstance(value["overall_score"], (int, float)):
        raise ValueError("Overall score must be numeric.")
    for field in ("strengths", "weaknesses", "recommendations", "question_performance"):
        if not isinstance(value[field], list):
            raise ValueError(f"Report field '{field}' must be a list.")
    return value


def create_evaluation(score, strengths, weaknesses, feedback, next_difficulty, recommended_topic):
    return {
        "score": score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "feedback": feedback,
        "next_difficulty": next_difficulty,
        "recommended_topic": recommended_topic,
    }