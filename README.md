# NL → SQL: Ask Your Database in English

A Streamlit app that turns plain-English questions into executable SQL using
Google Gemini, runs them against the Chinook sample database, and shows the
result with auto-generated charts. Includes a retry loop that asks the LLM to
fix its own queries when they fail.

## Features

- Natural-language → SQL via Gemini LLM reasoning
- Automatic retry on malformed queries (sends the DB error back to the LLM)
- SELECT-only safety filter (blocks INSERT/UPDATE/DELETE/DROP/etc.)
- Real-time results as a DataFrame + auto bar chart for small result sets
- Sidebar with live schema dump and example questions

## Local setup

1. Clone the repo and `cd` into it.

2. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Get a free Gemini API key at https://aistudio.google.com/apikey
   (verify the URL — Google has occasionally moved this page.)

4. Create your `.env`:

   ```bash
   cp .env.example .env
   ```
   Open `.env` and paste your key into `GOOGLE_API_KEY=...`.

5. Download the Chinook database:

   ```bash
   python setup_db.py
   ```

6. Run the app:

   ```bash
   streamlit run app.py
   ```

   It should open at http://localhost:8501.

## Deploying to Streamlit Community Cloud

1. Push everything **except** `.env` to a public GitHub repo. The `.gitignore`
   already excludes `.env`.

2. Commit `chinook.db` — Streamlit Cloud needs it. (Don't run `setup_db.py`
   on the cloud; just include the file in the repo. It's ~1 MB.)

3. Go to https://share.streamlit.io, sign in with GitHub, click "New app",
   and point it at your repo + `app.py`.

4. In the app's Settings → Secrets, paste:

   ```
   GOOGLE_API_KEY = "your_actual_key_here"
   ```

   Streamlit Cloud exposes these as environment variables, so `os.getenv()`
   in `llm.py` will pick it up the same way as your local `.env`.

5. Click Deploy. First boot takes 1–3 minutes.

## Project structure

```
nl-to-sql/
├── app.py            # Streamlit UI + retry loop orchestration
├── llm.py            # Gemini wrapper: generate_sql, fix_sql
├── db.py             # Schema introspection, safety filter, query execution
├── setup_db.py       # Downloads Chinook from GitHub
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## How the retry loop works

When you click Run:

1. `generate_sql(question, schema)` produces a first SQL attempt.
2. The safety filter checks it's a SELECT/WITH query with no modifying keywords.
3. The query runs. If it succeeds, results display.
4. If execution throws (or the safety check fails), the question + schema +
   failing SQL + error message are sent back via `fix_sql(...)`, and the new
   query is tried.
5. This repeats up to `MAX_RETRIES` times (default 3). All failed attempts
   are shown in a collapsed "details" panel above the results.

## Known limitations

- Free-tier Gemini has rate limits. Check current quotas at
  https://ai.google.dev/pricing.
- The schema dump fits in one prompt because Chinook is small (11 tables).
  Larger databases would need schema-pruning before prompting.
- The safety filter is keyword-based, not a full SQL parser; it's defense in
  depth, not a security boundary. For production, use a read-only DB user.
