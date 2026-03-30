# CrossMind Evidence Package

Verifiable results from CrossMind's adversarial stress testing and transparent trading pipeline.

## Files

### 1. `war_room_report.json`
**What:** Complete results from 6 historical crash scenario replays.
**Why it matters:** Proves the strategy survived real market catastrophes (Japan carry trade -24%, Iran tensions -13%, Tariff scare -13%).
**Key number:** 6/6 scenarios survived. 2 trades refused during Japan Carry Trade crash, saving est. $17.30.

### 2. `sample_refusal_proof.json`
**What:** A single refusal decision with full audit trail.
**Why it matters:** This is CrossMind's core innovation — a verifiable record showing exactly WHY the agent refused to trade, with SHA-256 hash chain integrity.
**Look for:** `decision: "REFUSE"`, `refusal_proof`, `prev_hash` → `entry_hash` chain.

### 3. `ledger_verification.png`
**What:** Screenshot of Trust Ledger hash chain verification passing.
**Why it matters:** Proves the append-only ledger has not been tampered with.

### 4. `dashboard_screenshot.png`
**What:** CrossMind Streamlit dashboard showing live status, trust ledger, and war room results.
**Why it matters:** Judges can see the complete system at a glance.

## Key Results

- **Survived:** 6/6 historical crash scenarios
- **Trades executed:** 6
- **Trades refused:** 2 (refusal rate: 33%)
- **Capital saved by refusals:** $17.30
- **Max drawdown:** 1.9% (circuit breaker at 5%)
- **Gatekeeper score:** 77/100
- **Trust Ledger:** SHA-256 chain valid
