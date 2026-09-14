from adaptive_engine import determine_next_difficulty
from evaluator import evaluate_answer
from question_generator import generate_question
from schemas import validate_report


def create_interview_session(role, experience, interview_type, difficulty, stage):
    return {
        "role": role,
        "experience": experience,
        "interview_type": interview_type,
        "difficulty": difficulty,
        "stage": stage,
        "previous_questions": [],
        "previous_topics": [],
        "answers": [],
        "evaluations": [],
        "question_answers": [],
    }


def get_next_question(session):
    question = generate_question(
        role=session["role"],
        experience=session["experience"],
        interview_type=session["interview_type"],
        difficulty=session["difficulty"],
        stage=session["stage"],
        previous_questions=session["previous_questions"],
        previous_topics=session["previous_topics"],
    )
    session["previous_questions"].append(question)
    return question


def process_candidate_answer(session, question, candidate_answer):
    evaluation = evaluate_answer(
        question=question,
        answer=candidate_answer,
        role=session["role"],
        experience=session["experience"],
        difficulty=session["difficulty"],
    )

    session["answers"].append(candidate_answer)
    session["evaluations"].append(evaluation)
    session["question_answers"].append({"question": question, "answer": candidate_answer})

    recommended_topic = evaluation.get("recommended_topic", "")
    if recommended_topic and recommended_topic not in session["previous_topics"]:
        session["previous_topics"].append(recommended_topic)

    next_difficulty = determine_next_difficulty(evaluation["score"], session["difficulty"])
    session["difficulty"] = next_difficulty

    return {
        "score": evaluation["score"],
        "strengths": evaluation["strengths"],
        "weaknesses": evaluation["weaknesses"],
        "feedback": evaluation["feedback"],
        "next_difficulty": next_difficulty,
        "recommended_topic": recommended_topic,
    }


def process_answer(session, question, answer):
    """Backward-compatible alias for older backend callers."""
    return process_candidate_answer(session, question, answer)


def run_interview_turn(session, question, answer):
    return process_candidate_answer(session, question, answer)


def generate_final_report(session):
    evaluations = session["evaluations"]
    answered_questions = session.get("question_answers", [])

    if not evaluations:
        return validate_report({
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "question_performance": [],
        })

    overall_score = round(sum(item["score"] for item in evaluations) / len(evaluations))
    strengths = []
    weaknesses = []
    recommendations = []
    question_performance = []

    for index, evaluation in enumerate(evaluations):
        strengths.extend(evaluation.get("strengths", []))
        weaknesses.extend(evaluation.get("weaknesses", []))
        topic = evaluation.get("recommended_topic", "")
        if topic:
            recommendations.append(topic)

        question = answered_questions[index]["question"] if index < len(answered_questions) else "Question unavailable"
        question_performance.append({
            "question": question,
            "score": evaluation["score"],
            "feedback": evaluation.get("feedback", ""),
        })

    return validate_report({
        "overall_score": overall_score,
        "strengths": list(dict.fromkeys(strengths)),
        "weaknesses": list(dict.fromkeys(weaknesses)),
        "recommendations": list(dict.fromkeys(recommendations)),
        "question_performance": question_performance,
    })
