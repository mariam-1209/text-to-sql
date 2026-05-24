"""
Database helpers.
Supports two modes:
  - file mode: query an on-disk SQLite database (e.g. chinook.db)
  - in-memory mode: build a SQLite database in RAM from uploaded CSVs

The 'db' parameter passed to most functions is either:
  - a string path (for file mode), or
  - a sqlite3.Connection object (for in-memory mode)
"""
import os
import re
import sqlite3
import pandas as pd


# ─────────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────────
def _connect(db):
    """Return a usable sqlite3 connection.
    If db is a string, open it. If db is already a Connection, return it as-is.
    The caller must NOT close a Connection passed in directly; we only close
    connections we opened ourselves (i.e. opened from a path).
    """
    if isinstance(db, sqlite3.Connection):
        return db, False  # (conn, should_close)
    return sqlite3.connect(db), True


# ─────────────────────────────────────────────────────────────
# Schema introspection
# ─────────────────────────────────────────────────────────────
def get_schema(db) -> str:
    """LLM-friendly schema dump."""
    conn, should_close = _connect(db)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name;"
        )
        tables = [row[0] for row in cur.fetchall()]

        lines = []
        for table in tables:
            cur.execute(f"PRAGMA table_info('{table}');")
            cols = cur.fetchall()
            col_strs = [f"{c[1]} {c[2]}" for c in cols]
            lines.append(f"TABLE {table} ({', '.join(col_strs)})")
        return "\n".join(lines)
    finally:
        if should_close:
            conn.close()


def get_schema_structured(db) -> dict:
    """Schema as {table_name: [(column_name, column_type), ...]} for UI cards."""
    conn, should_close = _connect(db)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name;"
        )
        tables = [row[0] for row in cur.fetchall()]

        out = {}
        for table in tables:
            cur.execute(f"PRAGMA table_info('{table}');")
            cols = cur.fetchall()
            out[table] = [(c[1], c[2] or "TEXT") for c in cols]
        return out
    finally:
        if should_close:
            conn.close()


# ─────────────────────────────────────────────────────────────
# Safety filter (unchanged from before)
# ─────────────────────────────────────────────────────────────
_FORBIDDEN = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER",
    "TRUNCATE", "CREATE", "REPLACE", "ATTACH", "DETACH",
    "PRAGMA", "VACUUM", "REINDEX",
]


def is_safe_query(sql: str) -> bool:
    """Allow only SELECT / WITH queries with no modifying keywords."""
    s = sql.strip()
    if not s:
        return False
    head = s.lstrip().upper()
    if not (head.startswith("SELECT") or head.startswith("WITH")):
        return False
    for kw in _FORBIDDEN:
        if re.search(r"\b" + kw + r"\b", s, flags=re.IGNORECASE):
            return False
    body = s.rstrip().rstrip(";")
    if ";" in body:
        return False
    return True


# ─────────────────────────────────────────────────────────────
# Query execution
# ─────────────────────────────────────────────────────────────
def execute_query(sql: str, db) -> pd.DataFrame:
    """Run a read-only query and return a DataFrame."""
    conn, should_close = _connect(db)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        if should_close:
            conn.close()


# ─────────────────────────────────────────────────────────────
# CSV → SQLite (in-memory)
# ─────────────────────────────────────────────────────────────
def _sanitize_table_name(filename: str) -> str:
    """
    Turn 'My Sales Q3.csv' into 'my_sales_q3'.
    SQLite identifiers must be alphanumeric + underscore; we also lowercase
    for consistency and to make queries easier to write.
    """
    base = os.path.splitext(os.path.basename(filename))[0]
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", base).strip("_").lower()
    if not cleaned:
        cleaned = "uploaded"
    # SQLite identifiers can't start with a number
    if cleaned[0].isdigit():
        cleaned = "t_" + cleaned
    return cleaned


def _sanitize_column_name(col: str) -> str:
    """Clean up CSV column names so they're SQL-friendly."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", str(col)).strip("_")
    if not cleaned:
        cleaned = "col"
    if cleaned[0].isdigit():
        cleaned = "c_" + cleaned
    return cleaned


def build_db_from_csvs(uploaded_files) -> tuple:
    """
    Build an in-memory SQLite database from one or more uploaded CSV files.

    Args:
        uploaded_files: list of Streamlit UploadedFile objects (each has .name
                        and supports .read() / pandas.read_csv())

    Returns:
        (conn, info) where:
            conn: sqlite3.Connection (in-memory, keep alive for the session)
            info: list of dicts, one per file, with keys:
                  - filename (original)
                  - table_name (sanitized)
                  - rows
                  - error (None if success, else error string)
    """
    # in-memory DB shared across this connection
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    info = []
    seen_table_names = set()

    for f in uploaded_files:
        entry = {"filename": f.name, "table_name": None, "rows": 0, "error": None}
        try:
            # Reset the file pointer in case it was read earlier
            try:
                f.seek(0)
            except Exception:
                pass

            df = pd.read_csv(f)

            # Sanitize column names
            df.columns = [_sanitize_column_name(c) for c in df.columns]

            # Pick a unique table name
            base_name = _sanitize_table_name(f.name)
            table_name = base_name
            n = 2
            while table_name in seen_table_names:
                table_name = f"{base_name}_{n}"
                n += 1
            seen_table_names.add(table_name)

            df.to_sql(table_name, conn, index=False, if_exists="replace")

            entry["table_name"] = table_name
            entry["rows"] = len(df)
        except Exception as e:
            entry["error"] = str(e)

        info.append(entry)

    return conn, info
