def determine_next_difficulty(score, current_difficulty):
    """
    Determines the next interview difficulty based on
    the candidate's performance.

    Score range: 0-100
    """

    if current_difficulty not in {"easy", "medium", "hard"}:
        raise ValueError("current_difficulty must be easy, medium, or hard")
    if not 0 <= score <= 100:
        raise ValueError("score must be between 0 and 100")

    if score >= 80:
        # Strong performance → increase difficulty
        if current_difficulty == "easy":
            return "medium"

        if current_difficulty == "medium":
            return "hard"

        return "hard"

    elif score >= 50:
        # Average performance → maintain difficulty
        return current_difficulty

    else:
        # Weak performance → decrease difficulty
        if current_difficulty == "hard":
            return "medium"

        if current_difficulty == "medium":
            return "easy"

        return "easy"