"""
Gemini wrapper: generate_sql() for first pass, fix_sql() for retries.
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY is not set. Add it to a .env file locally, "
        "or to Streamlit Cloud secrets when deployed."
    )

genai.configure(api_key=API_KEY)

# NOTE: model names change. If this errors with 'model not found', check
# https://ai.google.dev/gemini-api/docs/models and replace with a current model.
MODEL_NAME = "gemini-2.5-flash"


def _model():
    return genai.GenerativeModel(MODEL_NAME)


def _extract_text(response) -> str:
    """Safely pull text out of a Gemini response."""
    try:
        return response.text
    except Exception:
        # Fall back to parts if .text accessor fails (e.g. safety blocks, multi-part)
        if getattr(response, "candidates", None):
            parts = response.candidates[0].content.parts
            return "".join(getattr(p, "text", "") for p in parts)
        raise


def _clean_sql(text: str) -> str:
    """Strip markdown fences, leading 'sql' label, surrounding whitespace."""
    text = text.strip()
    # remove ```sql ... ``` or ``` ... ``` fences
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    # strip a leading 'sql' or 'SQL' label sometimes added by the model
    if text.lower().startswith("sql\n"):
        text = text[4:].lstrip()
    return text.rstrip(";").strip() + ";"


_GEN_PROMPT = """You are an expert at writing SQLite queries.

Given the SCHEMA below, write ONE SQL query that answers the QUESTION.

SCHEMA:
{schema}

RULES:
- Output ONLY the SQL query. No explanation, no markdown fences, no leading "sql:" label.
- Use only SELECT (CTEs with WITH are allowed). NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, REPLACE, ATTACH, or DETACH.
- Use SQLite syntax.
- Use table and column names exactly as shown in the schema.
- If the question asks for "top N" without specifying, use LIMIT 10.

QUESTION: {question}

SQL:"""


_FIX_PROMPT = """You previously wrote a SQL query that failed. Fix it.

SCHEMA:
{schema}

ORIGINAL QUESTION: {question}

YOUR PREVIOUS QUERY (which failed):
{bad_sql}

ERROR FROM DATABASE:
{error}

Write a corrected SQL query. Same rules apply:
- Output ONLY the SQL. No explanation, no markdown fences.
- SELECT / WITH only. No modifying statements.
- Use exact table and column names from the SCHEMA above.

CORRECTED SQL:"""


def generate_sql(question: str, schema: str) -> str:
    prompt = _GEN_PROMPT.format(schema=schema, question=question)
    response = _model().generate_content(prompt)
    return _clean_sql(_extract_text(response))


def fix_sql(question: str, schema: str, bad_sql: str, error: str) -> str:
    prompt = _FIX_PROMPT.format(
        schema=schema, question=question, bad_sql=bad_sql, error=error
    )
    response = _model().generate_content(prompt)
    return _clean_sql(_extract_text(response))
