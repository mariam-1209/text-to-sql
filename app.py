"""
Natural Language to SQL — Streamlit app (polished B&W)
"""
import html
import streamlit as st
from llm import generate_sql, fix_sql
from db import (
    get_schema,
    get_schema_structured,
    execute_query,
    is_safe_query,
    build_db_from_csvs,
)

DEFAULT_DB_PATH = "chinook.db"
MAX_RETRIES = 3

st.set_page_config(
    page_title="NL → SQL",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
    /* base */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, system-ui, sans-serif !important;
    }
    .stApp {
        background-color: #000000;
        /* subtle dot grid */
        background-image: radial-gradient(rgba(255,255,255,0.04) 1px, transparent 1px);
        background-size: 24px 24px;
    }

    /* hide streamlit chrome */
    #MainMenu, footer, header[data-testid="stHeader"] {visibility: hidden;}
    .block-container {padding-top: 2.5rem; padding-bottom: 4rem; max-width: 1200px;}

    /* ── sidebar ── */
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    .brand {
        font-size: 1.85rem;
        font-weight: 800;
        color: #FFFFFF;
        letter-spacing: -0.025em;
        margin: 0 0 0.15rem 0;
        line-height: 1;
    }
    .brand-sub {
        color: rgba(255, 255, 255, 0.4);
        font-size: 0.8rem;
        font-weight: 500;
        margin: 0 0 1.75rem 0;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.02em;
    }
    .sidebar-label {
        font-size: 0.7rem;
        font-weight: 600;
        color: rgba(255,255,255,0.35);
        letter-spacing: 0.1em;
        margin-bottom: 0.65rem;
        font-family: 'JetBrains Mono', monospace;
    }

    /* sidebar example buttons */
    section[data-testid="stSidebar"] .stButton button {
        text-align: left;
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.7);
        font-weight: 400;
        font-size: 0.83rem;
        padding: 0.65rem 0.85rem;
        white-space: normal;
        height: auto;
        line-height: 1.45;
        border-radius: 8px;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        margin-bottom: 0.3rem;
        position: relative;
        overflow: hidden;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255, 255, 255, 0.04);
        border-color: rgba(255, 255, 255, 0.3);
        color: #FFFFFF;
        transform: translateX(3px);
    }
    section[data-testid="stSidebar"] .stButton button:active {
        transform: translateX(1px);
    }

    /* ── hero ── */
    .hero {
        text-align: center;
        margin: 0.5rem 0 2.5rem 0;
        animation: fadeInDown 0.6s ease-out;
    }
    @keyframes fadeInDown {
        from {opacity: 0; transform: translateY(-12px);}
        to   {opacity: 1; transform: translateY(0);}
    }
    .hero h1 {
        font-size: 3.2rem;
        font-weight: 800;
        color: #FFFFFF;
        margin: 0;
        letter-spacing: -0.035em;
        line-height: 1.05;
    }
    .hero p {
        color: rgba(255, 255, 255, 0.5);
        font-size: 1rem;
        margin: 0.65rem 0 0 0;
        font-weight: 400;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.01em;
    }

    /* ── input field ── */
    .stTextInput input {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        padding: 1.15rem 1.25rem !important;
        font-size: 0.95rem !important;
        font-family: 'Inter', sans-serif !important;
        color: #FFFFFF !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .stTextInput input:hover {
        border-color: rgba(255, 255, 255, 0.35) !important;
        background: rgba(255, 255, 255, 0.035) !important;
        box-shadow: 0 0 32px rgba(255, 255, 255, 0.06) !important;
    }
    .stTextInput input:focus {
        border-color: rgba(255, 255, 255, 0.65) !important;
        background: rgba(255, 255, 255, 0.04) !important;
        box-shadow:
            0 0 0 3px rgba(255, 255, 255, 0.06),
            0 0 48px rgba(255, 255, 255, 0.12) !important;
        outline: none !important;
    }
    .stTextInput input::placeholder {color: rgba(255, 255, 255, 0.28) !important;}

    /* ── run button ── */
    .stButton button[kind="primary"] {
        background: #FFFFFF;
        border: 1px solid #FFFFFF;
        border-radius: 10px;
        font-size: 0.9rem;
        font-weight: 600;
        padding: 0.6rem 1.5rem;
        color: #000000;
        height: 56px;
        letter-spacing: -0.01em;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stButton button[kind="primary"]:hover {
        background: #E8E8E8;
        border-color: #E8E8E8;
        transform: translateY(-1px);
        box-shadow: 0 6px 24px rgba(255,255,255,0.12);
    }
    .stButton button[kind="primary"]:active {
        transform: translateY(0);
    }

    /* ── section labels ── */
    .section-label {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-size: 0.72rem;
        font-weight: 600;
        color: rgba(255,255,255,0.5);
        margin: 2.5rem 0 1rem 0;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }
    .section-label .line {
        flex: 1;
        height: 1px;
        background: rgba(255,255,255,0.08);
    }

    /* ── results fade-in ── */
    .results-wrap {animation: fadeInUp 0.5s cubic-bezier(0.4, 0, 0.2, 1);}
    @keyframes fadeInUp {
        from {opacity: 0; transform: translateY(12px);}
        to   {opacity: 1; transform: translateY(0);}
    }

    /* ── schema cards: native <details> for expand/collapse ── */
    details.table-card {
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 12px;
        padding: 0;
        margin-bottom: 0.75rem;
        overflow: hidden;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    details.table-card:hover {
        border-color: rgba(255,255,255,0.28);
        background: rgba(255,255,255,0.04);
        transform: translateY(-1px);
    }
    details.table-card[open] {
        border-color: rgba(255,255,255,0.3);
        background: rgba(255,255,255,0.04);
    }
    details.table-card summary {
        list-style: none;
        cursor: pointer;
        padding: 0.85rem 1.1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-weight: 600;
        font-size: 0.92rem;
        color: #FFFFFF;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.01em;
    }
    details.table-card summary::-webkit-details-marker {display:none;}
    details.table-card summary .chev {
        width: 18px; height: 18px;
        color: rgba(255,255,255,0.5);
        transition: transform 0.25s ease;
        font-size: 0.7rem;
    }
    details.table-card[open] summary .chev {transform: rotate(180deg); color: #FFFFFF;}
    details.table-card summary .count {
        font-size: 0.7rem;
        color: rgba(255,255,255,0.4);
        font-weight: 500;
        margin-left: 0.6rem;
    }
    .table-card-body {
        padding: 0.4rem 1.1rem 1rem 1.1rem;
        border-top: 1px solid rgba(255,255,255,0.06);
        animation: slideDown 0.25s ease-out;
    }
    @keyframes slideDown {
        from {opacity: 0; transform: translateY(-4px);}
        to   {opacity: 1; transform: translateY(0);}
    }
    .col-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.8rem;
        font-family: 'JetBrains Mono', monospace;
        padding: 0.32rem 0;
        color: rgba(255, 255, 255, 0.72);
        transition: color 0.15s ease;
    }
    .col-row:hover {color: #FFFFFF;}
    .col-row .col-name::before {
        content: "·";
        margin-right: 0.55rem;
        color: rgba(255,255,255,0.35);
    }
    .pill {
        font-size: 0.65rem;
        font-weight: 600;
        padding: 0.18rem 0.5rem;
        border-radius: 4px;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.04em;
        background: rgba(255, 255, 255, 0.07);
        color: rgba(255, 255, 255, 0.75);
        border: 1px solid rgba(255,255,255,0.06);
    }

    /* ── code blocks ── */
    pre, code {
        border-radius: 10px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    [data-testid="stCodeBlock"] {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        overflow: hidden;
    }

    /* ── metric cards ── */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 1.1rem 1.25rem;
        border-radius: 12px;
        transition: all 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: rgba(255,255,255,0.2);
        background: rgba(255,255,255,0.04);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.68rem !important;
        color: rgba(255, 255, 255, 0.45) !important;
        font-weight: 600 !important;
        font-family: 'JetBrains Mono', monospace !important;
        letter-spacing: 0.08em !important;
    }
    [data-testid="stMetricValue"] {
        font-weight: 800 !important;
        color: #FFFFFF !important;
        font-size: 2rem !important;
        letter-spacing: -0.02em !important;
    }

    /* ── dataframe ── */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        overflow: hidden;
    }

    /* ── tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 1rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.6rem 1.1rem;
        border-radius: 8px 8px 0 0;
        color: rgba(255, 255, 255, 0.45);
        font-weight: 500;
        font-size: 0.88rem;
        transition: color 0.2s ease;
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: -0.01em;
    }
    .stTabs [data-baseweb="tab"]:hover {color: rgba(255,255,255,0.8);}
    .stTabs [aria-selected="true"] {color: #FFFFFF !important;}
    .stTabs [data-baseweb="tab-highlight"] {background: #FFFFFF !important; height: 2px !important;}

    /* ── shimmer loader (replaces dull spinner text) ── */
    .shimmer {
        height: 56px;
        border-radius: 12px;
        background: linear-gradient(
            90deg,
            rgba(255,255,255,0.03) 0%,
            rgba(255,255,255,0.08) 50%,
            rgba(255,255,255,0.03) 100%
        );
        background-size: 200% 100%;
        animation: shimmerMove 1.4s ease-in-out infinite;
        display: flex;
        align-items: center;
        padding: 0 1.25rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: rgba(255,255,255,0.55);
        letter-spacing: 0.02em;
        border: 1px solid rgba(255,255,255,0.08);
    }
    @keyframes shimmerMove {
        0%   {background-position: 200% 0;}
        100% {background-position: -200% 0;}
    }
    .blinking-cursor {
        display: inline-block;
        width: 7px;
        height: 14px;
        background: rgba(255,255,255,0.7);
        margin-left: 6px;
        animation: blink 1s steps(2, start) infinite;
        vertical-align: middle;
    }
    @keyframes blink {to {visibility: hidden;}}

    /* ── expander ── */
    [data-testid="stExpander"] {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        background: rgba(255,255,255,0.02);
    }
    [data-testid="stExpander"] summary:hover {color: #FFFFFF;}

    /* ── scrollbar ── */
    ::-webkit-scrollbar {width: 8px; height: 8px;}
    ::-webkit-scrollbar-track {background: transparent;}
    ::-webkit-scrollbar-thumb {background: rgba(255,255,255,0.1); border-radius: 4px;}
    ::-webkit-scrollbar-thumb:hover {background: rgba(255,255,255,0.2);}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def render_table_card(name: str, columns: list) -> str:
    rows = "\n".join(
        f'<div class="col-row">'
        f'<span class="col-name">{html.escape(c)}</span>'
        f'<span class="pill">{html.escape(t.upper())}</span>'
        f"</div>"
        for c, t in columns
    )
    return (
        f'<details class="table-card">'
        f'<summary>'
        f'<span>{html.escape(name)}<span class="count">{len(columns)} cols</span></span>'
        f'<span class="chev">▼</span>'
        f'</summary>'
        f'<div class="table-card-body">{rows}</div>'
        f"</details>"
    )


# ─────────────────────────────────────────────────────────────
# Database selection — Chinook by default, or uploaded CSVs
# ─────────────────────────────────────────────────────────────
# `active_db` is what every query uses: either a path string (Chinook)
# or a sqlite3 Connection (user-uploaded data).
# We keep the user's uploaded connection in session_state so it survives reruns.

if "user_conn" not in st.session_state:
    st.session_state["user_conn"] = None
    st.session_state["user_tables_info"] = None


# ─────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand">NL → SQL</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">powered by gemini</div>', unsafe_allow_html=True)

    # ── Data source section ──
    st.markdown('<div class="sidebar-label">YOUR DATA</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "upload csv(s)",
        type=["csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        help="Upload one or more CSV files. Each becomes a queryable table. The filename becomes the table name.",
    )

    # If user uploads new files, rebuild the in-memory DB
    if uploaded:
        # only rebuild if the set of files actually changed
        new_signature = tuple(sorted((f.name, f.size) for f in uploaded))
        if st.session_state.get("user_files_signature") != new_signature:
            try:
                conn, info = build_db_from_csvs(uploaded)
                st.session_state["user_conn"] = conn
                st.session_state["user_tables_info"] = info
                st.session_state["user_files_signature"] = new_signature
                # clear any cached schema from the previous DB
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Failed to load CSVs: {e}")

    # Show button to clear uploads and go back to Chinook
    if st.session_state["user_conn"] is not None:
        if st.button("← back to chinook demo", use_container_width=True, key="reset_db"):
            st.session_state["user_conn"] = None
            st.session_state["user_tables_info"] = None
            st.session_state.pop("user_files_signature", None)
            st.cache_data.clear()
            st.rerun()

    # ── Example questions (only shown for Chinook) ──
    if st.session_state["user_conn"] is None:
        st.markdown('<div class="sidebar-label">TRY THESE</div>', unsafe_allow_html=True)
        examples = [
            "Which 5 customers have spent the most money?",
            "What are the top 10 best-selling tracks?",
            "How many albums does each artist have? Show top 10.",
            "What is the total revenue per country?",
            "Which genre has the most tracks?",
        ]
        for ex in examples:
            if st.button(ex, key=f"ex_{ex}", use_container_width=True):
                st.session_state["question"] = ex


# ─────────────────────────────────────────────────────────────
# Decide which database is active for the rest of the page
# ─────────────────────────────────────────────────────────────
if st.session_state["user_conn"] is not None:
    active_db = st.session_state["user_conn"]
    db_mode = "user"
else:
    active_db = DEFAULT_DB_PATH
    db_mode = "chinook"


# ─────────────────────────────────────────────────────────────
# Load schema
# ─────────────────────────────────────────────────────────────
try:
    schema_text = get_schema(active_db)
    schema_struct = get_schema_structured(active_db)
except Exception as e:
    st.error(f"Could not load database schema. Error: {e}")
    st.stop()


# Tell the user if their upload had any per-file issues
if db_mode == "user" and st.session_state["user_tables_info"]:
    bad = [t for t in st.session_state["user_tables_info"] if t.get("error")]
    if bad:
        with st.expander(f"⚠ {len(bad)} file(s) failed to load", expanded=True):
            for t in bad:
                st.markdown(f"**{t['filename']}** — {t['error']}")


# ─────────────────────────────────────────────────────────────
# Hero (dynamic based on which database is loaded)
# ─────────────────────────────────────────────────────────────
if db_mode == "chinook":
    hero_subtitle = "ask the chinook music database in plain english"
else:
    n_tables = len([t for t in st.session_state["user_tables_info"] if not t.get("error")])
    hero_subtitle = f"ask your data in plain english · {n_tables} table{'s' if n_tables != 1 else ''} loaded"

st.markdown(
    f"""
<div class="hero">
    <h1>NL → SQL</h1>
    <p>{hero_subtitle}</p>
</div>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# Input row
# ─────────────────────────────────────────────────────────────
col_input, col_button = st.columns([6, 1])
with col_input:
    question = st.text_input(
        "Your question",
        value=st.session_state.get("question", ""),
        placeholder="e.g. show me revenue by country, top customers, etc.",
        label_visibility="collapsed",
    )
with col_button:
    run = st.button("Run", type="primary", use_container_width=True)


# ─────────────────────────────────────────────────────────────
# Run + retry loop
# ─────────────────────────────────────────────────────────────
if run and question.strip():
    # custom shimmer loader instead of st.spinner
    loader = st.empty()
    loader.markdown(
        '<div class="shimmer">generating sql<span class="blinking-cursor"></span></div>',
        unsafe_allow_html=True,
    )

    try:
        sql = generate_sql(question, schema_text)
    except Exception as e:
        loader.empty()
        st.error(f"LLM call failed: {e}")
        st.stop()

    failed_attempts = []
    df = None
    final_sql = sql

    for attempt in range(1, MAX_RETRIES + 1):
        if not is_safe_query(sql):
            err = "Query rejected by safety filter (only SELECT / WITH allowed)."
            failed_attempts.append((sql, err))
            if attempt < MAX_RETRIES:
                loader.markdown(
                    f'<div class="shimmer">rewriting unsafe query · attempt {attempt + 1}'
                    f'<span class="blinking-cursor"></span></div>',
                    unsafe_allow_html=True,
                )
                try:
                    sql = fix_sql(question, schema_text, sql, err)
                except Exception as e:
                    loader.empty()
                    st.error(f"LLM retry failed: {e}")
                    break
            continue

        try:
            df = execute_query(sql, active_db)
            final_sql = sql
            break
        except Exception as e:
            err = str(e)
            failed_attempts.append((sql, err))
            if attempt < MAX_RETRIES:
                loader.markdown(
                    f'<div class="shimmer">fixing query · attempt {attempt + 1} of {MAX_RETRIES}'
                    f'<span class="blinking-cursor"></span></div>',
                    unsafe_allow_html=True,
                )
                try:
                    sql = fix_sql(question, schema_text, sql, err)
                except Exception as e2:
                    loader.empty()
                    st.error(f"LLM retry failed: {e2}")
                    break

    loader.empty()

    if df is not None:
        st.markdown('<div class="results-wrap">', unsafe_allow_html=True)
        total_attempts = len(failed_attempts) + 1

        st.markdown(
            '<div class="section-label">RESULTS<span class="line"></span></div>',
            unsafe_allow_html=True,
        )

        m1, m2, m3 = st.columns(3)
        m1.metric("ROWS", len(df))
        m2.metric("COLUMNS", len(df.columns))
        m3.metric("ATTEMPTS", total_attempts)

        if failed_attempts:
            with st.expander(f"took {total_attempts} attempts — view trace", expanded=False):
                for i, (bad_sql, err) in enumerate(failed_attempts, 1):
                    st.markdown(f"**attempt {i} — failed:**")
                    st.code(bad_sql, language="sql")
                    st.caption(f"error: {err}")

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        label_cols = [c for c in df.columns if c not in numeric_cols]
        can_chart = 0 < len(df) <= 50 and numeric_cols and label_cols

        tabs = st.tabs(["data", "sql", "chart"])
        with tabs[0]:
            st.dataframe(df, use_container_width=True, height=420)
        with tabs[1]:
            st.code(final_sql, language="sql")
        with tabs[2]:
            if can_chart:
                try:
                    chart_df = df.set_index(label_cols[0])[[numeric_cols[0]]]
                    st.bar_chart(chart_df, use_container_width=True)
                    st.caption(f"**{numeric_cols[0]}** by **{label_cols[0]}**")
                except Exception:
                    st.info("could not auto-generate a chart for this result.")
            elif len(df) == 0:
                st.info("no data to chart — query returned 0 rows.")
            elif len(df) > 50:
                st.info(f"too many rows ({len(df)}) for a clean chart. try LIMIT or aggregation.")
            elif not numeric_cols:
                st.info("no numeric columns to plot.")
            elif not label_cols:
                st.info("no label column to use as x-axis.")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.error(f"could not produce a working query after {MAX_RETRIES} attempts.")
        if failed_attempts:
            with st.expander("view attempts", expanded=True):
                for i, (bad_sql, err) in enumerate(failed_attempts, 1):
                    st.markdown(f"**attempt {i}:**")
                    st.code(bad_sql, language="sql")
                    st.caption(f"error: {err}")


# ─────────────────────────────────────────────────────────────
# Schema section (always visible, expandable cards)
# ─────────────────────────────────────────────────────────────
st.markdown(
    '<div class="section-label">SCHEMA<span class="line"></span></div>',
    unsafe_allow_html=True,
)

table_names = list(schema_struct.keys())
col_l, col_r = st.columns(2)
for i, name in enumerate(table_names):
    target = col_l if i % 2 == 0 else col_r
    with target:
        st.markdown(render_table_card(name, schema_struct[name]), unsafe_allow_html=True)
