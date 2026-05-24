"""
Database helpers for the Chinook SQLite database.
"""
import re
import sqlite3
import pandas as pd


def get_schema(db_path: str) -> str:
    """
    Return a compact, LLM-friendly schema dump of every user table.
    Example output:
        TABLE Artist (ArtistId INTEGER, Name NVARCHAR(120))
        TABLE Album (AlbumId INTEGER, Title NVARCHAR(160), ArtistId INTEGER)
    """
    conn = sqlite3.connect(db_path)
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
            # PRAGMA returns: (cid, name, type, notnull, dflt_value, pk)
            cur.execute(f"PRAGMA table_info('{table}');")
            cols = cur.fetchall()
            col_strs = [f"{c[1]} {c[2]}" for c in cols]
            lines.append(f"TABLE {table} ({', '.join(col_strs)})")
        return "\n".join(lines)
    finally:
        conn.close()


def get_schema_structured(db_path: str) -> dict:
    """
    Return the schema as {table_name: [(column_name, column_type), ...]}.
    Used by the UI to render each table as a styled card.
    """
    conn = sqlite3.connect(db_path)
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
            # c[1]=name, c[2]=type
            out[table] = [(c[1], c[2] or "TEXT") for c in cols]
        return out
    finally:
        conn.close()


# Words that should never appear in a generated query.
# Matched as whole words, case-insensitive.
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
    # remove trailing semicolons for the startswith check
    head = s.lstrip().upper()
    if not (head.startswith("SELECT") or head.startswith("WITH")):
        return False
    for kw in _FORBIDDEN:
        if re.search(r"\b" + kw + r"\b", s, flags=re.IGNORECASE):
            return False
    # also block multiple statements
    # crude: count semicolons inside the body (ignore one trailing semicolon)
    body = s.rstrip().rstrip(";")
    if ";" in body:
        return False
    return True


def execute_query(sql: str, db_path: str) -> pd.DataFrame:
    """Run a read-only query and return a DataFrame."""
    conn = sqlite3.connect(db_path)
    try:
        return pd.read_sql_query(sql, conn)
    finally:
        conn.close()