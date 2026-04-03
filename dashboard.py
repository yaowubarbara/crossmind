"""CrossMind Dashboard — Intelligence Terminal Style.

Shows: live status, trading decisions, refusal proofs, War Room results.

Supports two modes:
  - Live mode: uses Kraken CLI for real-time data
  - Demo mode: uses cached JSON data (for deployment without Kraken CLI)
    Set CROSSMIND_DEMO=true environment variable to enable.
"""

import streamlit as st
import json
import os
from datetime import datetime

DEMO_MODE = os.environ.get("CROSSMIND_DEMO", "false").lower() == "true"

# Page config
st.set_page_config(
    page_title="CROSSMIND // TERMINAL",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Intelligence Terminal CSS ──────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

    /* Base: near-black with faint green tint */
    .stApp { background-color: #080c08 !important; color: #a0b89a !important; }
    [data-testid="stHeader"] { background-color: #080c08 !important; }
    [data-testid="stSidebar"] { background-color: #060a06 !important; }
    .block-container { padding-top: 0.5rem; max-width: 1200px; }

    /* Scanline overlay */
    .stApp::before {
        content: "";
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            0deg, transparent, transparent 2px,
            rgba(0, 255, 65, 0.015) 2px, rgba(0, 255, 65, 0.015) 4px
        );
        pointer-events: none; z-index: 9999;
    }

    /* All text: monospace, terminal green */
    * { font-family: 'IBM Plex Mono', 'Courier New', monospace !important; }
    h1, h2, h3, h4 { color: #00ff41 !important; font-weight: 600 !important;
                      text-transform: uppercase !important; letter-spacing: 2px !important; }
    p, span, li, td, th, label, div,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] td,
    [data-testid="stMarkdownContainer"] th { color: #a0b89a !important; }

    /* Metric values */
    [data-testid="stMetricValue"] { color: #00ff41 !important; font-size: 1.6rem !important;
                                    font-family: 'Share Tech Mono', monospace !important; }
    [data-testid="stMetricLabel"] { color: #4a6a44 !important; text-transform: uppercase !important;
                                    font-size: 0.75rem !important; letter-spacing: 1.5px !important; }
    [data-testid="stMetricDelta"] { color: #f59e0b !important; }

    /* Card-style tabs as terminal screens */
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        background: #0a100a !important;
        border: 1px solid #1a3a1a !important;
        border-radius: 0 !important;
        padding: 8px 18px !important;
        color: #4a6a44 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
    }
    .stTabs [aria-selected="true"] {
        background: #0a1a0a !important;
        border-color: #00ff41 !important;
        color: #00ff41 !important;
        box-shadow: 0 0 8px rgba(0, 255, 65, 0.15);
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none; }
    .stTabs [data-baseweb="tab-border"] { display: none; }

    /* Metric card backgrounds */
    [data-testid="stMetric"],
    .stMetric { background: #0a100a !important; border: 1px solid #1a3a1a !important;
                border-radius: 0 !important; padding: 10px; }

    /* Dividers */
    .stDivider, hr { border-color: #1a3a1a !important; }

    /* Code blocks */
    code { color: #00ff41 !important; background-color: #0a100a !important; }
    pre { background-color: #0a100a !important; border: 1px solid #1a3a1a !important;
          border-radius: 0; padding: 12px; }
    pre code { color: #00ff41 !important; background-color: transparent !important; }
    [data-testid="stMarkdownContainer"] code,
    [data-testid="stMarkdownContainer"] pre,
    [data-testid="stMarkdownContainer"] pre code { color: #00ff41 !important; }

    /* Tables */
    table { border-collapse: collapse; }
    table th { color: #f59e0b !important; border-bottom: 1px solid #1a3a1a !important;
               text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px; }
    table td { color: #a0b89a !important; border-bottom: 1px solid #0e1a0e !important; }

    /* Buttons — terminal style */
    .stButton > button { background-color: #0a100a !important; color: #00ff41 !important;
                         border: 1px solid #00ff41 !important; border-radius: 0 !important;
                         text-transform: uppercase !important; letter-spacing: 1px !important;
                         font-size: 0.8rem !important; }
    .stButton > button:hover { background-color: #00ff41 !important; color: #080c08 !important; }

    /* Alerts */
    .stAlert p, .stAlert div { color: #a0b89a !important; }
    .stCaption, .stCaption p { color: #3a5a34 !important; }

    /* Decision cards — refusal = amber, execute = green */
    .intel-card-refuse { background: #12100a; border-left: 3px solid #f59e0b;
                         padding: 10px 14px; margin: 6px 0; font-size: 0.85rem; }
    .intel-card-execute { background: #0a120a; border-left: 3px solid #00ff41;
                          padding: 10px 14px; margin: 6px 0; font-size: 0.85rem; }

    /* War Room scenario cards */
    .scenario-card { background: #0a100a; border: 1px solid #1a3a1a;
                     padding: 14px; margin: 8px 0; }
    .scenario-survived { border-left: 3px solid #00ff41; }
    .scenario-failed { border-left: 3px solid #ff4444; }
</style>
""", unsafe_allow_html=True)


def load_ledger():
    """Load trust ledger entries from all scenario subdirectories."""
    entries = []
    records_dir = "trust_ledger/records"
    if not os.path.exists(records_dir):
        return entries
    root_ledger = os.path.join(records_dir, "ledger.jsonl")
    if os.path.exists(root_ledger):
        with open(root_ledger) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
    for subdir in sorted(os.listdir(records_dir)):
        sub_path = os.path.join(records_dir, subdir)
        if os.path.isdir(sub_path):
            ledger_file = os.path.join(sub_path, "ledger.jsonl")
            if os.path.exists(ledger_file):
                with open(ledger_file) as f:
                    for line in f:
                        if line.strip():
                            entries.append(json.loads(line))
    return entries


def load_war_room_results():
    """Load War Room results from cache."""
    results = []
    cache_dir = "war_room_cache"
    results_file = os.path.join(cache_dir, "results.json")
    if os.path.exists(results_file):
        with open(results_file) as f:
            results = json.load(f)
    return results


# ══════════════════════════════════════════════════════════
#  HEADER — Intelligence Briefing
# ══════════════════════════════════════════════════════════
now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
st.markdown(f"""
<div style="border: 1px solid #1a3a1a; padding: 20px 24px; margin-bottom: 16px;
            position: relative; background: #0a100a;">
    <div style="position: absolute; top: 8px; right: 12px;
                color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;">
        TERMINAL ACTIVE // {now}
    </div>
    <div style="color: #1a3a1a; font-size: 0.7rem; letter-spacing: 3px;
                margin-bottom: 8px;">▸ SYSTEM://CROSSMIND</div>
    <div style="color: #00ff41; font-size: 2.2rem; font-weight: 700;
                letter-spacing: 4px; font-family: 'Share Tech Mono', monospace;
                text-shadow: 0 0 20px rgba(0,255,65,0.3);">
        CROSSMIND</div>
    <div style="color: #4a6a44; font-size: 0.85rem; margin-top: 4px;
                letter-spacing: 1px;">
        RED-TEAMED AUTONOMOUS TRADING AGENT // CAPITAL PROTECTION SYSTEM</div>
    <div style="color: #f59e0b; font-size: 0.75rem; margin-top: 10px;
                letter-spacing: 2px; border-top: 1px solid #1a3a1a; padding-top: 8px;">
        ◈ CLASSIFIED // TRUST VERIFIED // SHA-256 HASH CHAIN ACTIVE</div>
</div>
""", unsafe_allow_html=True)

# ── Hero Metrics ───────────────────────────────────────────
entries = load_ledger()
if entries:
    refusals = [e for e in entries if e["decision"] == "REFUSE"]
    executions = [e for e in entries if e["decision"] == "EXECUTE"]
    total_saved = sum(
        (e.get("refusal_impact") or {}).get("would_have_lost", 0)
        for e in refusals if e.get("refusal_impact")
    )
    refusal_rate = len(refusals) / max(1, len(entries)) * 100

    st.markdown(f"""
    <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a;
                    padding: 14px 16px; text-align: center;">
            <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;
                        margin-bottom: 4px;">THREATS BLOCKED</div>
            <div style="color: #f59e0b; font-size: 1.8rem; font-weight: 700;
                        font-family: 'Share Tech Mono', monospace;
                        text-shadow: 0 0 10px rgba(245,158,11,0.3);">{len(refusals)}</div>
        </div>
        <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a;
                    padding: 14px 16px; text-align: center;">
            <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;
                        margin-bottom: 4px;">CAPITAL PRESERVED</div>
            <div style="color: #00ff41; font-size: 1.8rem; font-weight: 700;
                        font-family: 'Share Tech Mono', monospace;
                        text-shadow: 0 0 10px rgba(0,255,65,0.3);">${total_saved:,.2f}</div>
        </div>
        <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a;
                    padding: 14px 16px; text-align: center;">
            <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;
                        margin-bottom: 4px;">REFUSAL RATE</div>
            <div style="color: #f59e0b; font-size: 1.8rem; font-weight: 700;
                        font-family: 'Share Tech Mono', monospace;">{refusal_rate:.0f}%</div>
        </div>
        <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a;
                    padding: 14px 16px; text-align: center;">
            <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;
                        margin-bottom: 4px;">LEDGER RECORDS</div>
            <div style="color: #a0b89a; font-size: 1.8rem; font-weight: 700;
                        font-family: 'Share Tech Mono', monospace;">{len(entries)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "▸ LIVE STATUS", "▸ TRUST LEDGER", "▸ WAR ROOM", "▸ ARCHITECTURE"
])

with tab1:
    st.markdown("### ▸ Market Intelligence Feed")
    try:
        if DEMO_MODE:
            ticker = json.load(open("demo_data/ticker.json"))
            rsi_data = json.load(open("demo_data/rsi.json"))
            rsi = rsi_data["rsi"]
            balance_data = json.load(open("demo_data/balance.json"))
            usd_bal = balance_data.get("balances", {}).get("USD", {}).get("total", 10000)
        else:
            from kraken_client import KrakenClient
            from signal_generator import compute_rsi
            import config
            client = KrakenClient()
            ticker = client.ticker()
            candles = client.ohlc(pair=config.PAIR_KRAKEN, interval=config.CANDLE_INTERVAL)
            closes = [c["close"] for c in candles]
            rsi = compute_rsi(closes)
            balance_data = client.paper_balance()
            usd_bal = balance_data.get("balances", {}).get("USD", {}).get("total", 0)

        pct_change = ((ticker['last'] - ticker.get('open', ticker['last'])) / ticker.get('open', ticker['last']) * 100)
        signal_text = "◉ BUY SIGNAL" if rsi < 28 else "◉ SELL SIGNAL" if rsi > 65 else "○ HOLD"
        signal_color = "#00ff41" if rsi < 28 else "#ff4444" if rsi > 65 else "#4a6a44"
        rsi_color = "#ff4444" if rsi < 28 else "#00ff41" if rsi > 65 else "#f59e0b"

        st.markdown(f"""
        <div style="display: flex; gap: 8px;">
            <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a; padding: 14px;">
                <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;">BTC/USD</div>
                <div style="color: #00ff41; font-size: 1.6rem; font-weight: 700;
                            font-family: 'Share Tech Mono', monospace;">${ticker['last']:,.2f}</div>
                <div style="color: {'#00ff41' if pct_change >= 0 else '#ff4444'}; font-size: 0.85rem;">
                    {pct_change:+.2f}%</div>
            </div>
            <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a; padding: 14px;">
                <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;">RSI (14)</div>
                <div style="color: {rsi_color}; font-size: 1.6rem; font-weight: 700;
                            font-family: 'Share Tech Mono', monospace;">{rsi}</div>
                <div style="color: #4a6a44; font-size: 0.85rem;">4H Candles</div>
            </div>
            <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a; padding: 14px;">
                <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;">PAPER BALANCE</div>
                <div style="color: #a0b89a; font-size: 1.6rem; font-weight: 700;
                            font-family: 'Share Tech Mono', monospace;">${usd_bal:,.2f}</div>
                <div style="color: #4a6a44; font-size: 0.85rem;">Kraken Sandbox</div>
            </div>
            <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a; padding: 14px;">
                <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;">SIGNAL</div>
                <div style="color: {signal_color}; font-size: 1.4rem; font-weight: 700;
                            font-family: 'Share Tech Mono', monospace;">{signal_text}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if DEMO_MODE:
            st.markdown("""<div style="color: #3a5a34; font-size: 0.75rem; margin-top: 8px;
                          letter-spacing: 1px;">◈ DEMO MODE — CACHED INTEL</div>""",
                        unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Intel feed offline: {e}")

with tab2:
    st.markdown("### ▸ Trust Ledger — Decision Audit Trail")

    entries = load_ledger()
    if not entries:
        st.markdown("""<div style="color: #4a6a44; padding: 20px; border: 1px dashed #1a3a1a;
                      text-align: center;">NO RECORDS. RUN WAR ROOM TO GENERATE DATA.</div>""",
                    unsafe_allow_html=True)
    else:
        executions = [e for e in entries if e["decision"] == "EXECUTE"]
        refusals = [e for e in entries if e["decision"] == "REFUSE"]
        saved = sum(
            (e.get("refusal_impact") or {}).get("would_have_lost", 0)
            for e in refusals if e.get("refusal_impact")
        )

        st.markdown(f"""
        <div style="display: flex; gap: 8px; margin-bottom: 12px;">
            <div style="flex:1; background:#0a100a; border:1px solid #1a3a1a; padding:10px; text-align:center;">
                <div style="color:#3a5a34; font-size:0.65rem; letter-spacing:2px;">DECISIONS</div>
                <div style="color:#a0b89a; font-size:1.4rem; font-weight:700;">{len(entries)}</div>
            </div>
            <div style="flex:1; background:#0a100a; border:1px solid #1a3a1a; padding:10px; text-align:center;">
                <div style="color:#3a5a34; font-size:0.65rem; letter-spacing:2px;">EXECUTED</div>
                <div style="color:#00ff41; font-size:1.4rem; font-weight:700;">{len(executions)}</div>
            </div>
            <div style="flex:1; background:#0a100a; border:1px solid #1a3a1a; padding:10px; text-align:center;">
                <div style="color:#3a5a34; font-size:0.65rem; letter-spacing:2px;">REFUSED</div>
                <div style="color:#f59e0b; font-size:1.4rem; font-weight:700;">{len(refusals)}</div>
            </div>
            <div style="flex:1; background:#0a100a; border:1px solid #1a3a1a; padding:10px; text-align:center;">
                <div style="color:#3a5a34; font-size:0.65rem; letter-spacing:2px;">SAVED</div>
                <div style="color:#00ff41; font-size:1.4rem; font-weight:700;">${saved:,.2f}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("◈ VERIFY HASH CHAIN INTEGRITY"):
            from trust_ledger import TrustLedger
            tl = TrustLedger()
            if tl.verify_chain():
                st.success("CHAIN VALID — NO TAMPERING DETECTED")
            else:
                st.error("CHAIN BROKEN — POSSIBLE TAMPERING")

        st.markdown('<div style="border-top: 1px solid #1a3a1a; margin: 10px 0;"></div>',
                    unsafe_allow_html=True)

        for entry in reversed(entries[-20:]):
            is_refusal = entry["decision"] == "REFUSE"
            card_class = "intel-card-refuse" if is_refusal else "intel-card-execute"
            tag = "REFUSE" if is_refusal else "EXECUTE"
            tag_color = "#f59e0b" if is_refusal else "#00ff41"

            intent = entry.get("intent", {})
            action = intent.get("action", "?")
            pair = intent.get("pair", "?")
            price = intent.get("price", 0)
            ts = entry.get("timestamp", "")[:19]
            entry_hash = entry.get("entry_hash", "n/a")[:16]

            html = f"""<div class="{card_class}">
                <span style="color:{tag_color}; font-weight:700; font-size:0.8rem;">[{tag}]</span>
                <span style="color:#a0b89a;"> {action} {pair} @ ${price:,.2f}</span>
                <span style="color:#3a5a34; font-size:0.75rem;"> // {ts}</span>"""

            if is_refusal and entry.get("refusal_proof"):
                html += f"""<br><span style="color:#f59e0b; font-size:0.8rem;">
                    ▸ {entry['refusal_proof'][:120]}</span>"""
                ri = entry.get("refusal_impact") or {}
                if ri.get("saved_by_refusal"):
                    html += f"""<br><span style="color:#00ff41; font-size:0.8rem;">
                        ▸ SAVED: ${ri.get('would_have_lost', 0):,.2f}</span>"""
            elif not is_refusal and entry.get("result"):
                pnl = entry["result"].get("pnl")
                if pnl is not None:
                    pnl_color = "#00ff41" if pnl >= 0 else "#ff4444"
                    html += f"""<br><span style="color:{pnl_color}; font-size:0.8rem;">
                        ▸ PnL: ${pnl:+,.2f}</span>"""

            html += f"""<br><span style="color:#1a3a1a; font-size:0.7rem;">
                HASH: {entry_hash}...</span></div>"""
            st.markdown(html, unsafe_allow_html=True)

with tab3:
    st.markdown("### ▸ War Room — Adversarial Stress Testing")

    war_results = load_war_room_results()
    if not war_results:
        st.markdown("""<div style="color: #4a6a44; padding: 20px; border: 1px dashed #1a3a1a;
                      text-align: center;">NO WAR ROOM DATA. RUN STRESS TEST TO GENERATE.</div>""",
                    unsafe_allow_html=True)
    else:
        survived = sum(1 for r in war_results if r.get("survived"))
        total = len(war_results)
        surv_color = "#00ff41" if survived == total else "#f59e0b"

        st.markdown(f"""
        <div style="background: #0a100a; border: 1px solid #1a3a1a; padding: 16px;
                    margin-bottom: 12px; text-align: center;">
            <div style="color: #3a5a34; font-size: 0.7rem; letter-spacing: 2px;
                        margin-bottom: 4px;">SURVIVAL SCORE</div>
            <div style="color: {surv_color}; font-size: 2.4rem; font-weight: 700;
                        font-family: 'Share Tech Mono', monospace;
                        text-shadow: 0 0 15px {surv_color}40;">{survived}/{total}</div>
            <div style="color: #4a6a44; font-size: 0.8rem; margin-top: 4px;">
                SCENARIOS SURVIVED</div>
        </div>
        """, unsafe_allow_html=True)

        for r in war_results:
            survived_flag = r.get("survived", False)
            cb = r.get("circuit_breaker", False)
            border_class = "scenario-survived" if survived_flag else "scenario-failed"
            status = "● SURVIVED" if survived_flag else "✕ FAILED"
            status_color = "#00ff41" if survived_flag else "#ff4444"
            if cb:
                status = "◉ CIRCUIT BREAKER"
                status_color = "#f59e0b"

            scenario = r.get("scenario", "Unknown")
            dd = r.get("max_drawdown", 0)
            refs = r.get("refusals", 0)
            trades = r.get("total_trades", 0)
            final = r.get("final_capital", 0)

            st.markdown(f"""
            <div class="scenario-card {border_class}">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <span style="color: #a0b89a; font-weight: 600; font-size: 0.9rem;">
                            {scenario}</span>
                    </div>
                    <div style="color: {status_color}; font-weight: 700; font-size: 0.8rem;">
                        {status}</div>
                </div>
                <div style="display: flex; gap: 24px; margin-top: 8px; font-size: 0.8rem;">
                    <span style="color: #4a6a44;">MAX DD: <span style="color: {'#ff4444' if dd > 3 else '#a0b89a'};">{dd:.1f}%</span></span>
                    <span style="color: #4a6a44;">TRADES: <span style="color: #a0b89a;">{trades}</span></span>
                    <span style="color: #4a6a44;">REFUSALS: <span style="color: #f59e0b;">{refs}</span></span>
                    <span style="color: #4a6a44;">FINAL: <span style="color: #a0b89a;">${final:,.2f}</span></span>
                </div>
            </div>
            """, unsafe_allow_html=True)

with tab4:
    st.markdown("### ▸ System Architecture")

    st.markdown("""
    <div style="display: flex; gap: 8px; margin-bottom: 16px;">
        <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a; padding: 14px;">
            <div style="color: #00ff41; font-size: 0.8rem; letter-spacing: 2px;
                        margin-bottom: 10px; border-bottom: 1px solid #1a3a1a; padding-bottom: 6px;">
                DETERMINISTIC AGENTS</div>
            <div style="margin: 8px 0;">
                <span style="color: #00ff41;">●</span>
                <span style="color: #a0b89a; font-weight: 600;">ANALYST</span>
                <span style="color: #4a6a44;"> — RSI calculation, market state</span>
            </div>
            <div style="margin: 8px 0;">
                <span style="color: #00ff41;">●</span>
                <span style="color: #a0b89a; font-weight: 600;">STRATEGIST</span>
                <span style="color: #4a6a44;"> — Trade signal generation</span>
            </div>
            <div style="color: #3a5a34; font-size: 0.75rem; margin-top: 10px;
                        font-style: italic;">Fast. Reliable. No hallucination.</div>
        </div>
        <div style="flex: 1; background: #0a100a; border: 1px solid #1a3a1a; padding: 14px;">
            <div style="color: #f59e0b; font-size: 0.8rem; letter-spacing: 2px;
                        margin-bottom: 10px; border-bottom: 1px solid #1a3a1a; padding-bottom: 6px;">
                AI-POWERED AGENTS</div>
            <div style="margin: 8px 0;">
                <span style="color: #f59e0b;">●</span>
                <span style="color: #a0b89a; font-weight: 600;">RISK MANAGER</span>
                <span style="color: #4a6a44;"> — Approve / refuse trades</span>
            </div>
            <div style="margin: 8px 0;">
                <span style="color: #f59e0b;">●</span>
                <span style="color: #a0b89a; font-weight: 600;">ADVERSARY</span>
                <span style="color: #4a6a44;"> — Red team attacks</span>
            </div>
            <div style="color: #3a5a34; font-size: 0.75rem; margin-top: 10px;
                        font-style: italic;">Reasoning. Judgment. Natural language.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background: #0a100a; border: 1px solid #1a3a1a; padding: 16px; margin-bottom: 16px;">
        <div style="color: #00ff41; font-size: 0.8rem; letter-spacing: 2px;
                    margin-bottom: 10px;">DECISION PIPELINE</div>
        <pre style="color: #00ff41; background: transparent; border: none; padding: 0;
                    font-size: 0.85rem; line-height: 1.6;">
  Market Data ──▸ ANALYST ──▸ STRATEGIST ──▸ RISK MANAGER ──▸ Execute/Refuse ──▸ TRUST LEDGER
                                                   ▲
                                             ADVERSARY (War Room)</pre>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background: #0a100a; border: 1px solid #1a3a1a; padding: 16px;">
        <div style="color: #00ff41; font-size: 0.8rem; letter-spacing: 2px;
                    margin-bottom: 10px;">RISK PARAMETERS</div>
        <table style="width: 100%; font-size: 0.85rem;">
            <tr><td style="color: #4a6a44; padding: 4px 0;">Max Drawdown</td>
                <td style="color: #ff4444;">5% (circuit breaker)</td></tr>
            <tr><td style="color: #4a6a44; padding: 4px 0;">Max Consecutive Losses</td>
                <td style="color: #f59e0b;">3 (trading pause)</td></tr>
            <tr><td style="color: #4a6a44; padding: 4px 0;">Position Size</td>
                <td style="color: #a0b89a;">10% of capital</td></tr>
            <tr><td style="color: #4a6a44; padding: 4px 0;">Stop Loss / Take Profit</td>
                <td style="color: #a0b89a;">3% / 5%</td></tr>
            <tr><td style="color: #4a6a44; padding: 4px 0;">RSI Entry / Exit</td>
                <td style="color: #a0b89a;">&lt; 28 / &gt; 65</td></tr>
            <tr><td style="color: #4a6a44; padding: 4px 0;">Weekend Trading</td>
                <td style="color: #ff4444;">BLOCKED</td></tr>
            <tr><td style="color: #4a6a44; padding: 4px 0;">US Market Open</td>
                <td style="color: #ff4444;">BLOCKED</td></tr>
        </table>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown(f"""
<div style="border-top: 1px solid #1a3a1a; margin-top: 20px; padding-top: 10px;
            color: #1a3a1a; font-size: 0.7rem; letter-spacing: 1px; text-align: center;">
    CROSSMIND v1.0 // AI TRADING AGENTS HACKATHON // LABLAB.AI // KRAKEN CLI
</div>
""", unsafe_allow_html=True)
