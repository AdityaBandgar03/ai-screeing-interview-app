import json
from openai import AzureOpenAI
from app.providers.llm.base import LLMProvider


class AzureOpenAILLMProvider(LLMProvider):

    def __init__(self, endpoint, api_key, deployment_name):
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version="2024-02-15-preview"
        )
        self.deployment_name = deployment_name

    def generate_question_set(self, job_description: str, resume: str):
        """Generate one opening question that includes a greeting and intro ask. Returns dict with 'questions' (first question = greeting + ask)."""
        system_prompt = """You are a friendly AI Screening Interviewer.

This is a SHORT screening interview to evaluate whether the candidate is a basic fit for the role.

Rules:
- From the resume, identify the candidate's first name (or full name).
- The FIRST question must combine a short greeting and the opening ask in ONE natural sentence. Example: "Hi [Name], nice to meet you. Can you introduce yourself and tell me what drew you to this role?" or "Hi [Name], thanks for joining. To start, could you give a brief intro about your background?" Do NOT ask a technical question first.
- Ask beginner-friendly questions only. Do NOT ask deep system design or advanced theoretical questions.
- Keep tone natural and conversational. It should feel like a human recruiter speaking.
- Keep the combined greeting + question concise (max 2–3 short sentences).
- Avoid technical jargon unless clearly mentioned in the resume.

Return STRICT JSON only."""
        user_prompt = f"""Job Description:
{job_description}

Resume:
{resume}

From the resume, identify the candidate's name. Return a single opening "question" whose text is the greeting and first question combined (e.g. "Hi [Name], nice to meet you. Can you introduce yourself?").

Return JSON:
{{"questions": [{{"id": "Q1", "text": "<greeting using candidate name, then ask for intro/background in one flow>"}}]}}"""

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        questions = parsed.get("questions", [{"id": "Q1", "text": "Hi, nice to meet you. Can you introduce yourself?"}])
        return {"questions": questions}

    def get_next_prompt(
        self,
        job_description: str,
        resume: str,
        full_transcript: list,
        question_count: int,
    ) -> dict:
        """Return {decision, question, reason, evaluation, closing_message?}."""
        system_prompt = """You are a friendly AI Screening Interviewer conducting a SHORT job screening interview.

This is NOT a deep technical interview.
This is a beginner-friendly screening to evaluate basic role alignment.
Assume the candidate has 0-3 years of experience unless clearly senior in resume. Keep difficulty aligned accordingly.

Interview Guidelines:
1. Total MAIN questions must be strictly between 4 and 5.
2. Follow-up questions are allowed only if clarification is needed.
3. Keep the overall interview short.
4. Ask ONE question at a time.
5. Questions must be: beginner-friendly, practical, based on job description and resume, natural and conversational.
6. Do NOT ask advanced system design, architecture, or complex algorithm questions.
7. Do NOT repeat questions.
8. Keep questions short (max 2 sentences).
9. Maintain a friendly, professional tone.
10. When asking the next question or a follow-up, do NOT be monotonous. Briefly acknowledge the candidate's last answer with a short natural phrase before asking (e.g. "Oh okay," "Alright," "I see," "That makes sense," "Got it," "Interesting.") then ask the question. Put the acknowledgment and the question together in the "question" field so the conversation flows naturally.

Before deciding, internally think about: what skill has been evaluated, what remains untested, whether clarity is sufficient. Do NOT reveal internal reasoning.

Decision Rules:
- If the candidate's answer is vague, unclear, or incomplete → decision = "follow_up"
- If answer is clear and question_count < 4 → decision = "ask_new"
- If question_count is 4 and answer is acceptable → decision = "end"
- Never exceed 5 main questions. Keep the total interaction concise.

When ending: provide a short polite closing message and thank the candidate.

Respond ONLY in this JSON format:
{"decision": "ask_new" | "follow_up" | "end", "reason": "<brief reasoning>", "question": "<brief acknowledgment of their answer, then next question — or null if ending>", "evaluation": "<short screening evaluation>", "closing_message": "<only when decision is end, otherwise null>"}"""

        lines = []
        for i, pair in enumerate(full_transcript, 1):
            lines.append(f"Q{i}: {pair.get('question_text', '')}")
            lines.append(f"A{i}: {pair.get('answer_transcript', '')}")
        conv = "\n".join(lines) if lines else "(none yet)"
        latest = full_transcript[-1].get("answer_transcript", "") if full_transcript else ""

        user_prompt = f"""Job Description:
{job_description}

Candidate Resume:
{resume}

Total Questions Asked (main): {question_count}
Do not exceed 5 total main questions.

Conversation History:
{conv}

Candidate's Latest Answer:
{latest}"""

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        decision = parsed.get("decision", "end")
        question = parsed.get("question")
        if decision == "end":
            question = None
        return {
            "decision": decision,
            "question": question,
            "reason": parsed.get("reason", ""),
            "evaluation": parsed.get("evaluation", ""),
            "closing_message": parsed.get("closing_message"),
        }

    def evaluate_interview(
        self,
        job_description: str,
        resume: str,
        transcript_text: str,
    ) -> dict:
        """Evaluate candidate fit from JD, resume, and full Q&A transcript. Returns structured evaluation."""
        system_prompt = """You are an unbiased screening evaluator. Your task is to assess whether the candidate is a good fit for the role based ONLY on: 1) Job Description, 2) Candidate Resume, 3) Full interview transcript (questions and answers).

Be objective and fair. Base your assessment on clarity of answers, relevance to the role, and alignment with job requirements.
Do NOT make assumptions beyond what is stated in the resume and transcript.

Return STRICT JSON only with these exact keys:
- recommendation: one of "strong_fit", "fit", "weak_fit", "not_recommended"
- summary: 2-3 sentence overall assessment
- strengths: array of strings (key strengths observed)
- concerns: array of strings (gaps or concerns, if any)
- role_fit_score: number 1-5 (5 = best fit)
- suggested_next_step: one short sentence (e.g. "Invite for technical round" or "Reject")"""

        user_prompt = f"""Job Description:
{job_description}

Candidate Resume:
{resume}

Interview Transcript:
{transcript_text}

Evaluate and return JSON with: recommendation, summary, strengths, concerns, role_fit_score, suggested_next_step."""

        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
        return {
            "recommendation": parsed.get("recommendation", "fit"),
            "summary": parsed.get("summary", ""),
            "strengths": parsed.get("strengths") or [],
            "concerns": parsed.get("concerns") or [],
            "role_fit_score": parsed.get("role_fit_score", 3),
            "suggested_next_step": parsed.get("suggested_next_step", ""),
        }
