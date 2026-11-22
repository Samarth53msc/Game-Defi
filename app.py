"""
CircleFi — A blockchain-inspired Rotating Savings & Credit Association (ROSCA) app.

Run with:  streamlit run app.py
"""

import hashlib
import os
import sqlite3
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import streamlit as st

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "circlefi.db")
GENESIS_HASH = "0" * 64


# --------------------------------------------------------------------------- #
# Database helpers
# --------------------------------------------------------------------------- #

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS circles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contribution_amount REAL NOT NULL,
            cycle_length_days INTEGER NOT NULL,
            current_cycle INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            circle_id INTEGER NOT NULL REFERENCES circles(id),
            name TEXT NOT NULL,
            join_order INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            circle_id INTEGER NOT NULL REFERENCES circles(id),
            cycle INTEGER NOT NULL,
            entry_type TEXT NOT NULL,
            member_id INTEGER NOT NULL REFERENCES members(id),
            amount REAL NOT NULL,
            timestamp TEXT NOT NULL,
            prev_hash TEXT NOT NULL,
            hash TEXT NOT NULL
        );
        """
    )
    conn.commit()
    conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def compute_hash(circle_id, cycle, entry_type, member_id, amount, timestamp, prev_hash):
    payload = f"{circle_id}|{cycle}|{entry_type}|{member_id}|{amount}|{timestamp}|{prev_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def last_hash(conn, circle_id):
    row = conn.execute(
        "SELECT hash FROM ledger WHERE circle_id = ? ORDER BY id DESC LIMIT 1",
        (circle_id,),
    ).fetchone()
    return row[0] if row else GENESIS_HASH


def append_ledger(conn, circle_id, cycle, entry_type, member_id, amount):
    prev = last_hash(conn, circle_id)
    ts = now_iso()
    h = compute_hash(circle_id, cycle, entry_type, member_id, amount, ts, prev)
    conn.execute(
        """INSERT INTO ledger (circle_id, cycle, entry_type, member_id, amount, timestamp, prev_hash, hash)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (circle_id, cycle, entry_type, member_id, amount, ts, prev, h),
    )
    conn.commit()


# --------------------------------------------------------------------------- #
# Domain logic
# --------------------------------------------------------------------------- #

def create_circle(name, contribution_amount, cycle_length_days, member_names):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO circles (name, contribution_amount, cycle_length_days, current_cycle, created_at) "
        "VALUES (?, ?, ?, 1, ?)",
        (name, contribution_amount, cycle_length_days, now_iso()),
    )
    circle_id = cur.lastrowid
    for order, member_name in enumerate(member_names):
        conn.execute(
            "INSERT INTO members (circle_id, name, join_order) VALUES (?, ?, ?)",
            (circle_id, member_name.strip(), order),
        )
    conn.commit()
    conn.close()
    return circle_id


def list_circles():
    conn = get_conn()
    rows = conn.execute("SELECT id, name FROM circles ORDER BY id").fetchall()
    conn.close()
    return rows


def get_circle(circle_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, contribution_amount, cycle_length_days, current_cycle, created_at "
        "FROM circles WHERE id = ?",
        (circle_id,),
    ).fetchone()
    conn.close()
    return row


def get_members(circle_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, join_order FROM members WHERE circle_id = ? ORDER BY join_order",
        (circle_id,),
    ).fetchall()
    conn.close()
    return rows


def contributors_this_cycle(circle_id, cycle):
    conn = get_conn()
    rows = conn.execute(
        "SELECT member_id FROM ledger WHERE circle_id = ? AND cycle = ? AND entry_type = 'contribution'",
        (circle_id, cycle),
    ).fetchall()
    conn.close()
    return {r[0] for r in rows}


def add_contribution(circle_id, member_id):
    circle = get_circle(circle_id)
    cycle = circle[4]
    amount = circle[2]

    already = contributors_this_cycle(circle_id, cycle)
    if member_id in already:
        return False, "This member has already contributed for the current cycle."

    conn = get_conn()
    append_ledger(conn, circle_id, cycle, "contribution", member_id, amount)
    conn.close()

    members = get_members(circle_id)
    already = contributors_this_cycle(circle_id, cycle)
    if len(already) == len(members):
        trigger_payout(circle_id, cycle)
        return True, "Contribution recorded. All members have paid in — payout triggered!"
    return True, "Contribution recorded."


def trigger_payout(circle_id, cycle):
    members = get_members(circle_id)
    circle = get_circle(circle_id)
    num_members = len(members)
    contribution_amount = circle[2]
    pot = contribution_amount * num_members

    payee_index = (cycle - 1) % num_members
    payee_id = members[payee_index][0]

    conn = get_conn()
    append_ledger(conn, circle_id, cycle, "payout", payee_id, pot)
    conn.execute(
        "UPDATE circles SET current_cycle = current_cycle + 1 WHERE id = ?",
        (circle_id,),
    )
    conn.commit()
    conn.close()


def get_ledger(circle_id):
    conn = get_conn()
    rows = conn.execute(
        """SELECT l.id, l.cycle, l.entry_type, m.name, l.amount, l.timestamp, l.prev_hash, l.hash
           FROM ledger l JOIN members m ON l.member_id = m.id
           WHERE l.circle_id = ? ORDER BY l.id""",
        (circle_id,),
    ).fetchall()
    conn.close()
    return rows


def verify_chain(circle_id):
    conn = get_conn()
    rows = conn.execute(
        """SELECT id, circle_id, cycle, entry_type, member_id, amount, timestamp, prev_hash, hash
           FROM ledger WHERE circle_id = ? ORDER BY id""",
        (circle_id,),
    ).fetchall()
    conn.close()

    results = []
    expected_prev = GENESIS_HASH
    overall_ok = True
    for row in rows:
        (lid, cid, cycle, entry_type, member_id, amount, ts, prev_hash, stored_hash) = row
        recomputed = compute_hash(cid, cycle, entry_type, member_id, amount, ts, prev_hash)
        prev_ok = prev_hash == expected_prev
        hash_ok = recomputed == stored_hash
        ok = prev_ok and hash_ok
        overall_ok = overall_ok and ok
        results.append((lid, ok, prev_ok, hash_ok))
        expected_prev = stored_hash
    return overall_ok, results


def compute_trust_scores(circle_id):
    circle = get_circle(circle_id)
    completed_cycles = max(0, circle[4] - 1)
    members = get_members(circle_id)

    conn = get_conn()
    scores = {}
    for member_id, name, _order in members:
        if completed_cycles == 0:
            scores[member_id] = (name, 100.0)
            continue
        made = conn.execute(
            "SELECT COUNT(*) FROM ledger WHERE circle_id = ? AND member_id = ? AND entry_type = 'contribution' "
            "AND cycle <= ?",
            (circle_id, member_id, completed_cycles),
        ).fetchone()[0]
        scores[member_id] = (name, round(100.0 * made / completed_cycles, 1))
    conn.close()
    return scores


def seed_demo_data():
    """Create a sample circle with two completed cycles, for quick live demos."""
    circle_id = create_circle(
        "Demo Circle — Study Group Savings",
        100.0,
        7,
        ["Aadhithya", "Samarth", "Nidhi", "Naman"],
    )
    members = get_members(circle_id)
    # Cycle 1: everyone contributes -> auto payout to member[0]
    for member_id, _name, _order in members:
        add_contribution(circle_id, member_id)
    # Cycle 2: everyone contributes -> auto payout to member[1]
    for member_id, _name, _order in members:
        add_contribution(circle_id, member_id)
    return circle_id


# --------------------------------------------------------------------------- #
# Streamlit UI
# --------------------------------------------------------------------------- #

st.set_page_config(page_title="CircleFi", page_icon="🔗", layout="wide")
init_db()

st.sidebar.title("🔗 CircleFi")
st.sidebar.caption("Blockchain-inspired rotating savings circles")
light_mode = st.sidebar.toggle("☀️ Light mode", value=False)

if light_mode:
    PALETTE = dict(
        page_bg="#F1F3FB", sidebar_bg="#FFFFFF", card_bg="#FFFFFF", card_border="#E2E8F0",
        text="#0F172A", muted="#475569", accent="#4338CA", widget_bg="#FFFFFF",
        shadow="0 10px 30px -12px rgba(67, 56, 202, 0.18)",
        alert_bg="#FFFFFF",
    )
else:
    PALETTE = dict(
        page_bg="#0B1222", sidebar_bg="#0B1222", card_bg="#121B2E", card_border="#233049",
        text="#F8FAFC", muted="#AEBBD1", accent="#4F46E5", widget_bg="#121B2E",
        shadow="0 10px 30px -10px rgba(0, 0, 0, 0.55)",
        alert_bg="#121B2E",
    )

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

    html, body, [class*="css"]  {{ font-family: 'Inter', sans-serif; }}
    h1, h2, h3 {{ font-family: 'Space Grotesk', sans-serif !important; color: {PALETTE['text']} !important; }}

    [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ background: {PALETTE['page_bg']}; }}
    [data-testid="stSidebar"] {{ background: {PALETTE['sidebar_bg']}; border-right: 1px solid {PALETTE['card_border']}; }}
    html, body, p, span, label, [class*="css"] {{ color: {PALETTE['text']}; }}
    .hero-sub, .hero-sub b {{ color: inherit; }}

    /* Hero banner: fixed dark-navy brand strip with soft decorative glow blobs */
    .hero-banner {{
        position: relative;
        overflow: hidden;
        background: linear-gradient(135deg, #0B1222 0%, #1B2444 60%, #312E81 100%);
        border: 1px solid #233049;
        border-radius: 24px;
        padding: 40px 46px;
        margin-bottom: 28px;
        box-shadow: {PALETTE['shadow']};
    }}
    .hero-banner::before, .hero-banner::after {{
        content: "";
        position: absolute;
        border-radius: 50%;
        filter: blur(60px);
        opacity: 0.55;
        z-index: 0;
        pointer-events: none;
    }}
    .hero-banner::before {{
        width: 280px; height: 280px;
        background: #4F46E5;
        top: -120px; right: -60px;
    }}
    .hero-banner::after {{
        width: 220px; height: 220px;
        background: #2DD4BF;
        bottom: -110px; left: 10%;
    }}
    .hero-banner > * {{ position: relative; z-index: 1; }}
    .hero-eyebrow {{
        font-family: 'Space Grotesk', sans-serif;
        letter-spacing: 2px;
        text-transform: uppercase;
        font-size: 0.8rem;
        font-weight: 600;
        color: #2DD4BF;
        margin-bottom: 6px;
    }}
    .hero-title {{
        font-family: 'Space Grotesk', sans-serif !important;
        font-size: 2.6rem;
        font-weight: 700;
        color: #F8FAFC !important;
        margin: 0 0 8px 0;
    }}
    .hero-sub {{
        color: #AEBBD1 !important;
        font-size: 1.05rem;
        max-width: 760px;
        line-height: 1.5;
    }}
    .hero-sub b {{ color: #F8FAFC !important; }}

    /* Custom stat cards (replaces plain st.metric look) */
    .stats-row {{ display: flex; gap: 20px; margin: 4px 0 8px 0; flex-wrap: wrap; }}
    .stat-card {{
        flex: 1;
        min-width: 180px;
        background: {PALETTE['card_bg']};
        border: 1px solid {PALETTE['card_border']};
        border-radius: 20px;
        padding: 22px 24px;
        box-shadow: {PALETTE['shadow']};
        transition: transform 0.15s ease;
    }}
    .stat-icon {{
        width: 40px; height: 40px;
        display: flex; align-items: center; justify-content: center;
        border-radius: 12px;
        background: linear-gradient(135deg, #4F46E5, #2DD4BF);
        font-size: 1.1rem;
        margin-bottom: 14px;
    }}
    .stat-value {{ font-family: 'Space Grotesk', sans-serif; font-size: 2rem; font-weight: 700; color: {PALETTE['text']}; line-height: 1; }}
    .stat-label {{ color: {PALETTE['muted']}; font-size: 0.85rem; margin-top: 6px; }}

    div[data-testid="stMetric"] {{
        background: {PALETTE['card_bg']};
        border: 1px solid {PALETTE['card_border']};
        border-radius: 20px;
        padding: 18px 22px;
        box-shadow: {PALETTE['shadow']};
    }}
    div[data-testid="stMetric"] label {{ color: {PALETTE['muted']} !important; }}
    div[data-testid="stMetricValue"] {{ color: {PALETTE['text']} !important; }}

    [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stTextArea"] textarea {{
        background: {PALETTE['widget_bg']} !important;
        color: {PALETTE['text']} !important;
        border-color: {PALETTE['card_border']} !important;
        border-radius: 12px !important;
    }}

    .stButton > button {{
        border-radius: 999px;
        font-weight: 600;
        background: {PALETTE['widget_bg']};
        color: {PALETTE['text']};
        border: 1px solid {PALETTE['card_border']};
        transition: transform 0.12s ease, box-shadow 0.12s ease;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: {PALETTE['shadow']};
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #4F46E5, #4338CA);
        color: #FFFFFF;
        border: none;
    }}

    /* Softer, rounder alert boxes (success/error/warning/info) with accent left border */
    div[data-testid="stAlert"] {{
        background: {PALETTE['alert_bg']} !important;
        border-radius: 14px !important;
        border: 1px solid {PALETTE['card_border']} !important;
        box-shadow: {PALETTE['shadow']};
    }}

    /* Sidebar nav: pill-style highlight on the selected page */
    [data-testid="stSidebar"] label[data-baseweb="radio"] {{
        border-radius: 12px;
        padding: 8px 10px;
        margin-bottom: 2px;
        transition: background 0.12s ease;
    }}
    [data-testid="stSidebar"] label[data-baseweb="radio"]:hover {{
        background: {PALETTE['card_bg']};
    }}

    div[data-testid="stDataFrame"] {{
        border-radius: 16px;
        overflow: hidden;
        box-shadow: {PALETTE['shadow']};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Overview", "➕ Create Circle", "🤝 Join & Contribute", "📜 Ledger & Verification", "📊 Trust & Dashboard"],
)

circles = list_circles()
circle_options = {f"{name} (#{cid})": cid for cid, name in circles}


# ---- Overview ---------------------------------------------------------- #
if page == "🏠 Overview":
    st.markdown(
        """
        <div class="hero-banner">
            <div class="hero-eyebrow">Fintech &middot; Blockchain-inspired &middot; Streamlit MVP</div>
            <div class="hero-title">🔗 CircleFi</div>
            <div class="hero-sub">
                Digitizing rotating savings circles (ROSCAs) with a tamper-evident ledger.
                A small group pools a fixed contribution every cycle. One member receives the
                full pot each cycle, on a rotating basis, until everyone has been paid out once.
                Every contribution and payout is written to an append-only <b>hash-chained
                ledger</b> &mdash; the same core idea behind a blockchain &mdash; so the whole
                group can verify that nothing has been tampered with, without needing a
                crypto wallet or paying gas fees.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total_members = 0
    total_pot_cycles = 0
    if circles:
        conn = get_conn()
        total_members = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
        total_pot_cycles = conn.execute(
            "SELECT COUNT(*) FROM ledger WHERE entry_type = 'payout'"
        ).fetchone()[0]
        conn.close()

    st.markdown(
        f"""
        <div class="stats-row">
            <div class="stat-card">
                <div class="stat-icon">🔵</div>
                <div class="stat-value">{len(circles)}</div>
                <div class="stat-label">Active circles</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">👥</div>
                <div class="stat-value">{total_members}</div>
                <div class="stat-label">Total members</div>
            </div>
            <div class="stat-card">
                <div class="stat-icon">💰</div>
                <div class="stat-value">{total_pot_cycles}</div>
                <div class="stat-label">Payouts completed</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    if not circles:
        st.info("No circles yet. Create one, or load sample data to try the app instantly.")
    if st.button("⚡ Seed sample demo circle"):
        seed_demo_data()
        st.success("Demo circle created with 4 members and 2 completed cycles.")
        st.rerun()


# ---- Create Circle ------------------------------------------------------ #
elif page == "➕ Create Circle":
    st.title("Create a Savings Circle")
    with st.form("create_circle_form"):
        name = st.text_input("Circle name", placeholder="e.g. Study Group Savings")
        contribution_amount = st.number_input("Contribution per member, per cycle ($)", min_value=1.0, value=50.0, step=5.0)
        cycle_length_days = st.number_input("Cycle length (days)", min_value=1, value=7, step=1)
        members_raw = st.text_area(
            "Members (one name per line, in payout order)",
            placeholder="Alice\nBob\nCharlie\nDiana",
            height=120,
        )
        submitted = st.form_submit_button("Create circle")

    if submitted:
        member_names = [line.strip() for line in members_raw.splitlines() if line.strip()]
        if not name.strip():
            st.error("Please enter a circle name.")
        elif len(member_names) < 2:
            st.error("A circle needs at least 2 members.")
        else:
            circle_id = create_circle(name.strip(), contribution_amount, int(cycle_length_days), member_names)
            st.success(f"Circle '{name}' created with {len(member_names)} members (#{circle_id}).")
            st.rerun()


# ---- Join & Contribute --------------------------------------------------- #
elif page == "🤝 Join & Contribute":
    st.title("Join & Contribute")
    if not circles:
        st.warning("No circles exist yet. Create one first.")
    else:
        choice = st.selectbox("Select a circle", list(circle_options.keys()))
        circle_id = circle_options[choice]
        circle = get_circle(circle_id)
        members = get_members(circle_id)
        cycle = circle[4]
        contributed = contributors_this_cycle(circle_id, cycle)

        st.subheader(f"{circle[1]} — Cycle {cycle}")
        st.caption(f"Contribution: \\${circle[2]:.2f} per member · Pot this cycle: \\${circle[2] * len(members):.2f}")
        st.progress(len(contributed) / len(members), text=f"{len(contributed)} / {len(members)} members have paid in this cycle")

        cols = st.columns(len(members))
        for col, (member_id, mname, _order) in zip(cols, members):
            with col:
                st.write(f"**{mname}**")
                if member_id in contributed:
                    st.success("Paid ✅")
                else:
                    st.error("Pending")

        st.divider()
        pending_members = [(mid, mname) for mid, mname, _ in members if mid not in contributed]
        if not pending_members:
            st.info("Everyone has contributed this cycle — the payout has already been triggered. Check the Ledger tab.")
        else:
            member_choice = st.selectbox(
                "Who is contributing?",
                [f"{mname} (#{mid})" for mid, mname in pending_members],
            )
            if st.button("Submit contribution", type="primary"):
                mid = int(member_choice.split("#")[-1].rstrip(")"))
                ok, msg = add_contribution(circle_id, mid)
                if ok:
                    st.success(msg)
                    if "payout triggered" in msg.lower():
                        st.balloons()
                else:
                    st.error(msg)
                st.rerun()


# ---- Ledger & Verification ----------------------------------------------- #
elif page == "📜 Ledger & Verification":
    st.title("Ledger & Verification")
    if not circles:
        st.warning("No circles exist yet. Create one first.")
    else:
        choice = st.selectbox("Select a circle", list(circle_options.keys()))
        circle_id = circle_options[choice]
        rows = get_ledger(circle_id)

        if rows:
            df = pd.DataFrame(
                rows,
                columns=["id", "cycle", "type", "member", "amount", "timestamp", "prev_hash", "hash"],
            )
            df["hash"] = df["hash"].str[:12] + "…"
            df["prev_hash"] = df["prev_hash"].str[:12] + "…"
            df["type"] = df["type"].map({"contribution": "💳 contribution", "payout": "💰 payout"})
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "amount": st.column_config.NumberColumn("amount", format="$%.2f"),
                },
            )
        else:
            st.info("No ledger entries yet for this circle.")

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Verify chain integrity"):
                overall_ok, results = verify_chain(circle_id)
                if overall_ok:
                    st.success("Ledger verified: every entry's hash matches its recorded data and the previous entry — no tampering detected.")
                else:
                    st.error("TAMPERING DETECTED. The following ledger entries do not match their recorded hash:")
                    broken = [r for r in results if not r[1]]
                    st.write(pd.DataFrame(broken, columns=["ledger_id", "ok", "prev_hash_ok", "hash_ok"]))

        with col2:
            with st.expander("⚠️ Simulate tampering (for demo purposes)"):
                st.caption(
                    "Directly edits a past ledger entry's amount in the database, bypassing the hash chain — "
                    "then re-run Verify to see it get caught."
                )
                if rows and st.button("Tamper with the first ledger entry's amount"):
                    conn = get_conn()
                    conn.execute(
                        "UPDATE ledger SET amount = amount * 10 "
                        "WHERE id = (SELECT MIN(id) FROM ledger WHERE circle_id = ?)",
                        (circle_id,),
                    )
                    conn.commit()
                    conn.close()
                    st.warning("Entry tampered with. Click 'Verify chain integrity' to see it detected.")
                    st.rerun()


# ---- Trust & Dashboard ---------------------------------------------------- #
elif page == "📊 Trust & Dashboard":
    st.title("Trust Scores & Circle Dashboard")
    if not circles:
        st.warning("No circles exist yet. Create one first.")
    else:
        choice = st.selectbox("Select a circle", list(circle_options.keys()))
        circle_id = circle_options[choice]
        circle = get_circle(circle_id)
        members = get_members(circle_id)

        scores = compute_trust_scores(circle_id)
        score_df = pd.DataFrame(
            [(name, score) for name, score in scores.values()],
            columns=["Member", "Trust score (%)"],
        )
        st.subheader("Trust scores")
        trust_chart = (
            alt.Chart(score_df)
            .mark_bar(cornerRadiusTopLeft=8, cornerRadiusTopRight=8, size=60)
            .encode(
                x=alt.X("Member:N", sort=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Trust score (%):Q", scale=alt.Scale(domain=[0, 100])),
                color=alt.Color(
                    "Trust score (%):Q",
                    scale=alt.Scale(scheme="redyellowgreen", domain=[0, 100]),
                    legend=None,
                ),
                tooltip=["Member", "Trust score (%)"],
            )
            .properties(height=320)
        )
        st.altair_chart(trust_chart, use_container_width=True)

        rows = get_ledger(circle_id)
        if rows:
            df = pd.DataFrame(
                rows,
                columns=["id", "cycle", "type", "member", "amount", "timestamp", "prev_hash", "hash"],
            )
            contrib_df = df[df["type"] == "contribution"]
            pot_by_cycle = contrib_df.groupby("cycle")["amount"].sum().cumsum().reset_index()
            pot_by_cycle.columns = ["Cycle", "Cumulative pot"]
            st.subheader("Cumulative pot contributed over time")
            pot_chart = (
                alt.Chart(pot_by_cycle)
                .mark_area(line={"color": "#4F46E5"}, color=alt.Gradient(
                    gradient="linear",
                    stops=[
                        alt.GradientStop(color="#0B1222", offset=0),
                        alt.GradientStop(color="#4F46E5", offset=1),
                    ],
                    x1=1, x2=1, y1=1, y2=0,
                ))
                .encode(x=alt.X("Cycle:O"), y=alt.Y("Cumulative pot:Q"), tooltip=["Cycle", "Cumulative pot"])
                .properties(height=280)
            )
            st.altair_chart(pot_chart, use_container_width=True)

            payout_df = df[df["type"] == "payout"][["cycle", "member", "amount", "timestamp"]]
            st.subheader("Payout history")
            if payout_df.empty:
                st.caption("No payouts yet — still waiting on contributions for the current cycle.")
            else:
                st.dataframe(payout_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No activity yet in this circle.")

        st.divider()
        st.caption(
            f"Circle status: cycle {circle[4]} in progress · "
            f"{len(members)} members · \\${circle[2]:.2f} contribution per member per cycle."
        )
