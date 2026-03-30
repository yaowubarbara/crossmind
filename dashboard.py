"""CrossMind Dashboard — Streamlit-based visualization.

Shows: live status, trading decisions, refusal proofs, War Room results.
"""

import streamlit as st
import json
import os
import hashlib
from datetime import datetime

# Page config
st.set_page_config(
    page_title="CrossMind Dashboard",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS — dark trading terminal theme (green + gold, no purple)
st.markdown("""
<style>
    .stApp { background-color: #0a0a1a; }
    .block-container { padding-top: 1rem; }
    h1 { background: linear-gradient(135deg, #10b981, #f59e0b);
         -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stMetric { background: #12122a; border: 1px solid #1e1e3a;
                border-radius: 12px; padding: 12px; }
    .refusal-card { background: #1a1000; border: 1px solid #f59e0b;
                    border-radius: 8px; padding: 12px; margin: 8px 0; }
    .execute-card { background: #001a0a; border: 1px solid #10b981;
                    border-radius: 8px; padding: 12px; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)


def load_ledger():
    """Load trust ledger entries."""
    ledger_file = "trust_ledger/records/ledger.jsonl"
    entries = []
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


# Header
st.title("CrossMind")
st.caption("*A red-teamed transparent trading agent that proves when refusing to trade protects capital.*")

# Hero metrics — Refusal Impact front and center
entries = load_ledger()
if entries:
    refusals = [e for e in entries if e["decision"] == "REFUSE"]
    total_saved = sum(
        e.get("refusal_impact", {}).get("would_have_lost", 0)
        for e in refusals if e.get("refusal_impact")
    )
    hero1, hero2, hero3, hero4 = st.columns(4)
    with hero1:
        st.metric("Total Refusals", f"🛡️ {len(refusals)}")
    with hero2:
        st.metric("Capital Saved by Refusals", f"${total_saved:,.2f}")
    with hero3:
        executions = [e for e in entries if e["decision"] == "EXECUTE"]
        refusal_rate = len(refusals) / max(1, len(entries)) * 100
        st.metric("Refusal Rate", f"{refusal_rate:.0f}%")
    with hero4:
        st.metric("Trust Ledger Entries", f"{len(entries)}")

    if total_saved > 0:
        st.success(f"CrossMind has avoided an estimated **${total_saved:,.2f}** in potential losses by refusing unsafe trades.")

st.divider()

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Live Status", "🛡️ Trust Ledger", "⚔️ War Room", "📐 Architecture"])

with tab1:
    st.subheader("Live Trading Status")

    # Try to get live data
    try:
        from kraken_client import KrakenClient
        from signal_generator import compute_rsi
        import config

        client = KrakenClient()
        ticker = client.ticker()
        candles = client.ohlc(pair=config.PAIR_KRAKEN, interval=config.CANDLE_INTERVAL)
        closes = [c["close"] for c in candles]
        rsi = compute_rsi(closes)
        balance = client.paper_balance()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("BTC/USD", f"${ticker['last']:,.2f}",
                      f"{((ticker['last'] - ticker['open']) / ticker['open'] * 100):+.2f}%")
        with col2:
            rsi_color = "🔴" if rsi < 28 else "🟢" if rsi > 65 else "🟡"
            st.metric("RSI (14)", f"{rsi_color} {rsi}")
        with col3:
            usd_bal = balance.get("balances", {}).get("USD", {}).get("total", 0)
            st.metric("Paper Balance", f"${usd_bal:,.2f}")
        with col4:
            signal = "HOLD"
            if rsi < 28:
                signal = "🟢 BUY"
            elif rsi > 65:
                signal = "🔴 SELL"
            else:
                signal = "⬜ HOLD"
            st.metric("Signal", signal)

    except Exception as e:
        st.warning(f"Could not fetch live data: {e}")
        st.info("Run the Orchestrator first to generate trading data.")

with tab2:
    st.subheader("Trust Ledger — Every Decision Recorded")

    entries = load_ledger()

    if not entries:
        st.info("No ledger entries yet. Run the Orchestrator or War Room to generate data.")
    else:
        # Stats
        executions = [e for e in entries if e["decision"] == "EXECUTE"]
        refusals = [e for e in entries if e["decision"] == "REFUSE"]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Decisions", len(entries))
        with col2:
            st.metric("Executions", len(executions))
        with col3:
            st.metric("Refusals", f"🛡️ {len(refusals)}")
        with col4:
            # Calculate total saved
            saved = sum(
                e.get("refusal_impact", {}).get("would_have_lost", 0)
                for e in refusals
                if e.get("refusal_impact")
            )
            st.metric("Capital Saved", f"${saved:,.2f}")

        # Entries
        # Hash chain verification button
        st.divider()
        if st.button("🔐 Verify Trust Ledger Integrity"):
            from trust_ledger import TrustLedger
            tl = TrustLedger()
            if tl.verify_chain():
                st.success("✅ SHA-256 hash chain is VALID. No tampering detected.")
            else:
                st.error("❌ Hash chain BROKEN. Data may have been tampered with.")

        st.divider()
        for entry in reversed(entries[-20:]):  # Show last 20
            is_refusal = entry["decision"] == "REFUSE"
            css_class = "refusal-card" if is_refusal else "execute-card"
            icon = "🛡️ REFUSE" if is_refusal else "✅ EXECUTE"

            intent = entry.get("intent", {})
            action = intent.get("action", "?")
            pair = intent.get("pair", "?")
            price = intent.get("price", 0)

            html = f"""
            <div class="{css_class}">
                <strong>{icon}</strong> — {action} {pair} @ ${price:,.2f}<br>
                <small style="color: #888;">{entry.get('timestamp', '')[:19]}</small>
            """

            if is_refusal and entry.get("refusal_proof"):
                html += f"""<br><small style="color: #f59e0b;">
                    Reason: {entry['refusal_proof'][:150]}
                </small>"""

                if entry.get("refusal_impact", {}).get("saved_by_refusal"):
                    saved_amt = entry["refusal_impact"]["would_have_lost"]
                    html += f"""<br><small style="color: #44ff44;">
                        💰 This refusal saved est. ${saved_amt:,.2f}
                    </small>"""

            elif not is_refusal and entry.get("result"):
                result = entry["result"]
                pnl = result.get("pnl", None)
                if pnl is not None:
                    color = "#44ff44" if pnl > 0 else "#ff4444"
                    html += f"""<br><small style="color: {color};">
                        PnL: ${pnl:+,.2f}
                    </small>"""

            # Hash
            html += f"""<br><small style="color: #666;">
                Hash: {entry.get('entry_hash', 'n/a')[:16]}...
            </small></div>"""

            st.markdown(html, unsafe_allow_html=True)

with tab3:
    st.subheader("War Room — Adversarial Stress Testing")

    war_results = load_war_room_results()
    if not war_results:
        st.warning("No War Room data. Run `python war_room.py` to generate results.")
    else:
        survived = sum(1 for r in war_results if r.get("survived"))
        total = len(war_results)
        st.metric("Survival Score", f"{survived}/{total}")

        for r in war_results:
            status = "✅ Survived" if r.get("survived") else "❌ Failed"
            if r.get("circuit_breaker"):
                status = "🛑 Circuit Breaker"
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**{r.get('scenario', 'Unknown')}**")
            with col2:
                st.write(status)
            with col3:
                st.write(f"DD: {r.get('max_drawdown', 0):.1f}%")
            with col4:
                st.write(f"Refusals: {r.get('refusals', 0)}")

with tab4:
    st.subheader("4-Agent Architecture")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### Deterministic Agents
        | Agent | Role | Status |
        |-------|------|--------|
        | 🟢 **Analyst** | RSI calculation, market state | ✅ Active |
        | 🟢 **Strategist** | Trade signal generation | ✅ Active |

        *Deterministic = fast, reliable, no hallucination*
        """)

    with col2:
        st.markdown("""
        ### AI-Powered Agents
        | Agent | Role | Status |
        |-------|------|--------|
        | 🟡 **Risk Manager** | Approve/refuse trades | ✅ Active |
        | 🟡 **Adversary** | Red team attacks | ✅ War Room |

        *AI = reasoning, judgment, natural language*
        """)

    st.divider()
    st.markdown("""
    ### Decision Pipeline
    ```
    Market Data → Analyst → Strategist → Risk Manager → Execute/Refuse → Trust Ledger
                                              ↑
                                        Adversary (War Room)
    ```
    """)

    st.markdown("""
    ### Risk Parameters
    | Parameter | Value |
    |-----------|-------|
    | Max Drawdown | 5% (circuit breaker) |
    | Max Consecutive Losses | 3 (trading pause) |
    | Position Size | 10% of capital |
    | Stop Loss | 3% |
    | Take Profit | 5% |
    | RSI Entry | < 28 |
    | RSI Exit | > 65 |
    | No Weekend Trading | ✅ |
    | No US Market Open | ✅ |
    """)

# Footer
st.divider()
st.caption("CrossMind — AI Trading Agents Hackathon (lablab.ai) — Built with Kraken CLI")
