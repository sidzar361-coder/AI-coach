from .models import FinalReport, InterviewSession, RoundNumber


def generate_final_report(session: InterviewSession) -> FinalReport:
    evaluations_by_id = {evaluation.id: evaluation for evaluation in session.evaluations}
    question_by_id = {question.id: question for question in session.questions}
    strengths = []
    weaknesses = []
    recommendations = []
    question_performance = []

    for answer in session.answers:
        evaluation = evaluations_by_id.get(answer.evaluation_id)
        question = question_by_id.get(answer.question_id)
        if evaluation is None or question is None:
            continue
        strengths.extend(evaluation.strengths)
        weaknesses.extend(evaluation.weaknesses)
        recommendations.extend(evaluation.recommended_topics)
        question_performance.append(
            {
                "round": answer.round_number.value,
                "question": question.text,
                "answer": answer.text,
                "score": evaluation.score,
                "feedback": evaluation.feedback,
            }
        )

    scored_rounds = [
        score
        for round_number, score in session.round_scores.items()
        if int(round_number) < RoundNumber.FINAL_EVALUATION.value and score is not None
    ]
    overall_score = round(sum(scored_rounds) / len(scored_rounds), 2) if scored_rounds else None
    round_performance = [
        {
            "round": int(round_number),
            "score": score,
            "status": session.round_state(RoundNumber(int(round_number))).status.value,
        }
        for round_number, score in session.round_scores.items()
    ]

    return FinalReport(
        candidate_profile=session.candidate_profile,
        round_scores=session.round_scores.copy(),
        overall_score=overall_score,
        strengths=list(dict.fromkeys(strengths)),
        weaknesses=list(dict.fromkeys(weaknesses)),
        recommendations=list(dict.fromkeys(recommendations)),
        recommended_topics=session.recommended_topics.copy(),
        difficulty_progression=session.difficulty_progression.copy(),
        round_performance=round_performance,
        question_performance=question_performance,
    )