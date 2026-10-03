import json
import os
import re
from functools import lru_cache
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from services.pdf_service import extract_pdf_text, split_pdf_text


GEMMA_MODEL = os.getenv("GEMMA_MODEL", "gemma-3-27b-it")


@lru_cache(maxsize=1)
def get_llm():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")

    return ChatGoogleGenerativeAI(
        model=GEMMA_MODEL,
        google_api_key=api_key,
        temperature=0.35,
        max_output_tokens=6000,
        max_retries=2,
    )


def run_prompt(system: str, human: str) -> str:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            ("human", human),
        ]
    )

    chain = prompt | get_llm() | StrOutputParser()

    return chain.invoke({}).strip()


# =========================================================
# AI TUTOR
# =========================================================

TUTOR_SYSTEM = """
You are StudyForge AI, a patient university-level AI tutor.

Create accurate, structured, exam-friendly learning material.

Do not invent references or claim certainty when the topic is ambiguous.

Use:
- clear headings
- short paragraphs
- bullets
- examples
- common mistakes
- a mini self-check
- a concise recap

If the learner asks a follow-up, answer it in the context of the topic.

Respect the requested language.

Return Markdown only.
"""


# =========================================================
# STUDY PLANNER
# =========================================================

PLAN_SYSTEM = """
You are StudyForge AI, an expert academic study planner.

Create a realistic day-by-day plan based on:
- topic
- available minutes per day
- number of days
- learner level

Include:
- daily objectives
- study blocks
- active recall/practice
- review
- milestones
- final assessment/revision stage

Do not promise mastery.

Keep the workload feasible.

Return Markdown only.
"""


# =========================================================
# QUIZ
# =========================================================

# IMPORTANT:
# Do NOT use { } here because LangChain ChatPromptTemplate
# treats them as template variables.
#
# We intentionally describe the JSON structure using words
# instead of literal braces.

QUIZ_SYSTEM = """
You create high-quality educational multiple-choice quizzes.

Return ONLY valid JSON.

The JSON must contain these top-level fields:

title: string
instructions: string
questions: array

Each question object must contain:

question: string
options: array containing exactly four strings
answer: integer from 0 to 3
explanation: string

Rules:

1. Every question must have exactly four options.
2. There must be exactly one correct answer.
3. The answer field must be a zero-based integer.
4. Do not use A/B/C/D labels inside the option text.
5. Explanations must teach why the answer is correct.
6. Avoid trick questions.
7. Avoid unsupported facts.
8. Respect the requested language.
9. Do not return Markdown.
10. Do not return code fences.
11. Do not add any text before or after the JSON.
"""


# =========================================================
# PDF
# =========================================================

PDF_SYSTEM = """
You are a grounded PDF study assistant.

Answer ONLY from the supplied PDF excerpts.

If the answer is not supported by the excerpts, respond exactly:

NOT_FOUND_IN_PDF

Do not use outside knowledge to fill gaps.

If the PDF contains conflicting information, mention the conflict.

Answer concisely but explain the evidence from the document.
"""


# =========================================================
# TUTOR GENERATION
# =========================================================

def generate_tutor(topic, level, language, follow_up=""):
    return run_prompt(
        TUTOR_SYSTEM,
        f"""
Topic: {topic}
Learner level: {level}
Language: {language}
Previous/follow-up request: {follow_up or "Create the initial lesson."}

Build the lesson with:

# Topic

## Learning Objectives

## Core Concept

## Step-by-Step Explanation

## Example

## Practical/Application Notes

## Common Mistakes

## Quick Self-Check

## Summary
""",
    )


# =========================================================
# STUDY PLAN GENERATION
# =========================================================

def generate_study_plan(topic, minutes, days, level, language):
    return run_prompt(
        PLAN_SYSTEM,
        f"""
Topic: {topic}
Daily study time: {minutes} minutes
Plan duration: {days} days
Level: {level}
Language: {language}

Use this structure:

# {topic} — Study Plan

## Goal

## Strategy

## Day-by-Day Plan

For every day include:

- Objective
- Study block(s)
- Practice / active recall
- Review task
- Estimated minutes

## Weekly/Phase Milestones

## Final Assessment

## Revision Strategy
""",
    )


# =========================================================
# QUIZ GENERATION
# =========================================================

def generate_quiz(topic, difficulty, count, language):

    raw = run_prompt(
        QUIZ_SYSTEM,
        f"""
Topic: {topic}
Difficulty: {difficulty}
Number of questions: {count}
Language: {language}

Generate exactly {count} questions.

Return only valid JSON.
Do not use Markdown code fences.
Do not add explanations outside the JSON.
""",
    )

    raw = clean_json_response(raw)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Gemma returned invalid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError("Gemma returned an invalid quiz object.")

    questions = data.get("questions")

    if not isinstance(questions, list):
        raise ValueError("Quiz questions field is missing or invalid.")

    if len(questions) != count:
        raise ValueError(
            f"Gemma returned {len(questions)} questions instead of {count}."
        )

    validated_questions = []

    for index, q in enumerate(questions, start=1):

        if not isinstance(q, dict):
            raise ValueError(
                f"Question {index} is not a valid object."
            )

        question = q.get("question")
        options = q.get("options")
        answer = q.get("answer")
        explanation = q.get("explanation")

        # -----------------------------
        # Validate question
        # -----------------------------

        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                f"Question {index} has invalid question text."
            )

        # -----------------------------
        # Validate options
        # -----------------------------

        if not isinstance(options, list):
            raise ValueError(
                f"Question {index} options are invalid."
            )

        if len(options) != 4:
            raise ValueError(
                f"Question {index} must have exactly 4 options."
            )

        if not all(
            isinstance(option, str) and option.strip()
            for option in options
        ):
            raise ValueError(
                f"Question {index} contains invalid options."
            )

        # -----------------------------
        # Validate answer
        # -----------------------------

        # bool is technically an int in Python,
        # so explicitly reject it.
        if isinstance(answer, bool) or not isinstance(answer, int):
            raise ValueError(
                f"Question {index} answer must be an integer."
            )

        if answer not in range(4):
            raise ValueError(
                f"Question {index} answer must be between 0 and 3."
            )

        # -----------------------------
        # Validate explanation
        # -----------------------------

        if not isinstance(explanation, str):
            explanation = ""

        validated_questions.append(
            {
                "question": question.strip(),
                "options": [
                    option.strip()
                    for option in options
                ],
                "answer": answer,
                "explanation": explanation.strip(),
            }
        )

    return {
        "title": str(
            data.get("title") or f"{topic} Quiz"
        ),
        "instructions": str(
            data.get("instructions")
            or "Choose the best answer for each question."
        ),
        "questions": validated_questions,
    }


# =========================================================
# QUIZ JSON CLEANER
# =========================================================

def clean_json_response(text: str) -> str:

    text = text.strip()

    # Remove ```json ... ```
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s*```$",
        "",
        text,
    )

    text = text.strip()

    # Sometimes models add text before JSON.
    # Try to extract the outermost JSON object.
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]

    return text.strip()


# =========================================================
# PDF QUESTION ANSWERING
# =========================================================

def answer_pdf_question(path: Path, question: str):

    text = extract_pdf_text(path)

    chunks = split_pdf_text(text)

    relevant = retrieve_chunks(
        question,
        chunks,
        top_k=6,
    )

    context = "\n\n--- PDF EXCERPT ---\n\n".join(
        relevant
    )

    answer = run_prompt(
        PDF_SYSTEM,
        f"""
PDF EXCERPTS:

{context}

QUESTION:

{question}

Return either a grounded answer or exactly:

NOT_FOUND_IN_PDF
""",
    )

    if "NOT_FOUND_IN_PDF" in answer.upper():
        return "NOT_FOUND_IN_PDF"

    return answer


# =========================================================
# PDF RETRIEVAL
# =========================================================

def retrieve_chunks(question, chunks, top_k=6):

    q_tokens = set(
        tokenize(question)
    )

    q_phrases = [
        phrase
        for phrase in re.findall(
            r"[A-Za-z0-9][A-Za-z0-9 -]{3,}",
            question.lower(),
        )
    ]

    scored = []

    for index, chunk in enumerate(chunks):

        c_tokens = set(
            tokenize(chunk)
        )

        overlap = len(
            q_tokens & c_tokens
        )

        phrase_bonus = sum(
            2
            for phrase in q_phrases
            if phrase in chunk.lower()
        )

        score = overlap + phrase_bonus

        scored.append(
            (
                score,
                index,
                chunk,
            )
        )

    scored.sort(
        reverse=True,
        key=lambda item: (
            item[0],
            -item[1],
        ),
    )

    selected = [
        item[2]
        for item in scored[:top_k]
    ]

    if not selected:
        return chunks[:top_k]

    return selected


# =========================================================
# TOKENIZER
# =========================================================

def tokenize(text):

    return re.findall(
        r"[a-zA-Z0-9]{2,}",
        text.lower(),
    )