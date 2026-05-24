# NL → SQL

Ask any database in plain English. An LLM writes the SQL, the app runs it, and if the query breaks it sends the error back to the LLM to fix itself.

**→ [Live demo](https://text-to-sql-mariam.streamlit.app)**

![Screenshot](screenshot.png)

---

## What it does

- Type a question like *"which country has the most customers"* and get back a result table, the generated SQL, and an auto-chart
- Comes preloaded with the Chinook sample database (a digital music store with 11 related tables)
- Or upload your own CSVs — each file becomes a queryable table, and you can write questions that JOIN across them

## How it works

The interesting part isn't the LLM call — it's what happens when the LLM gets it wrong.

1. **Generate** — question + schema → Gemini returns a SQL query
2. **Filter** — reject anything that isn't a pure `SELECT` (no `DROP`, `UPDATE`, `INSERT`, multiple statements, etc.)
3. **Execute** — run the query against SQLite
4. **Repair** — if execution throws, feed the question, schema, broken SQL, and the database's error message back to the LLM and ask it to fix the query. Try up to 3 times.
5. **Render** — show the result as a table, the final SQL in a code block, and an auto-generated bar chart when the shape fits

Every failed attempt is logged and viewable in the UI, so you can see exactly what the LLM tried and what error it hit.

## Tech

Streamlit · Google Gemini · SQLite · pandas

## Run locally

```bash
git clone https://github.com/mariam-1209/text-to-sql.git
cd text-to-sql
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python setup_db.py                                     # downloads Chinook
echo "GOOGLE_API_KEY=your_key_here" > .env             # get a free key at aistudio.google.com/apikey
streamlit run app.py
```
