QUESTION_GENERATION_PROMPT = """
You are a professional technical interviewer conducting a formal interview.

Generate ONE interview question using the candidate information provided.

Candidate information:
- Role: {role}
- Experience: {experience}
- Interview type: {interview_type}
- Difficulty: {difficulty}
- Interview stage: {stage}

Previously asked questions:
{previous_questions}

Previously covered topics:
{previous_topics}

Requirements:

1. Generate a relevant question for the specified role.
2. Match the requested difficulty.
3. Do not repeat previous questions.
4. Avoid questions that are too easy or too difficult.
5. Prefer practical and role-relevant questions.
6. Maintain a professional interviewer tone.
7. Return only the question.
"""


ANSWER_EVALUATION_PROMPT = """
You are a professional technical interviewer.

Evaluate the candidate's answer objectively.

Interview Question:
{question}

Candidate Answer:
{answer}

Candidate Role:
{role}

Candidate Experience:
{experience}

Current Difficulty:
{difficulty}

Evaluate the answer based on:

1. Technical correctness
2. Understanding of the concept
3. Depth of reasoning
4. Relevance to the question
5. Completeness
6. Practical application
7. Clarity of explanation

Important rules:

- Do not score based primarily on grammar.
- Do not reward an answer simply because it is long.
- Do not penalize concise answers if they are technically complete.
- Identify incorrect technical claims.
- Distinguish between partial knowledge and complete understanding.
- Consider the candidate's experience level.
- Provide actionable professional feedback.

Return ONLY valid JSON.

JSON format:

{{
    "score": 0,
    "strengths": [],
    "weaknesses": [],
    "feedback": "",
    "recommended_difficulty": "easy",
    "recommended_topic": ""
}}
"""


def build_question_prompt(
    role,
    experience,
    interview_type,
    difficulty,
    stage,
    previous_questions,
    previous_topics,
):
    return QUESTION_GENERATION_PROMPT.format(
        role=role,
        experience=experience,
        interview_type=interview_type,
        difficulty=difficulty,
        stage=stage,
        previous_questions=previous_questions or "None",
        previous_topics=previous_topics or "None",
    )


def build_evaluation_prompt(question, answer, role, experience, difficulty):
    return ANSWER_EVALUATION_PROMPT.format(
        question=question,
        answer=answer,
        role=role,
        experience=experience,
        difficulty=difficulty,
    )