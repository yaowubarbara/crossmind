# CrossMind Evidence Package

Verifiable results from CrossMind's adversarial stress testing and transparent trading pipeline.

## Files

### 1. `war_room_report_v2.json`
**What:** Complete results from 11 historical scenario replays (9 crashes + 2 bull markets).
**Why it matters:** Proves the strategy survived real market catastrophes including Terra/LUNA (-54%), COVID crash (-54%), FTX collapse (-30%), and Japan carry trade unwind (-24%).
**Key numbers:** 11/11 scenarios survived, 66 total refusals, max drawdown 2.9%, Proof of Preservation Alpha 28x.

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

- **Survived:** 11/11 historical scenarios (9 crashes + 2 bull markets)
- **Total refusals:** 66 across all 11 scenarios
- **Refusal confirmation rate:** 100% (all 66 refusals retrospectively validated by subsequent price declines in crash scenarios, verified against Kraken OHLCV data)
- **Max drawdown:** 2.9% (circuit breaker at 5%)
- **A/B test:** CrossMind 11/11 survived vs. Momentum Chaser 7/11 (4 blown accounts)
- **Trust Ledger:** SHA-256 chain valid, on-chain anchored
- **Proof of Preservation Alpha (PPA): 28x**

## Proof of Preservation Alpha

PPA measures how much capital CrossMind's refusal decisions protected versus what was actually lost in trading. It answers: "Did the refusal engine earn its keep?"

### Methodology

For each refused trade: **Capital Protected = Position Size × Market Drop %**

PPA ratio = Total Capital Protected / Absolute Realized Losses

### PPA Breakdown by Scenario

| Scenario | Market Drop | Refusals | Capital At Risk | Capital Protected | Actual PnL |
|----------|-------------|----------|-----------------|-------------------|------------|
| Terra/LUNA Collapse | -54% | 28 | $14,000 | $7,560 | -$182 |
| COVID Crash | -54% | 16 | $8,000 | $4,320 | -$271 |
| March Correction | -26% | 18 | $9,000 | $2,340 | -$72 |
| Japan Carry Trade | -24% | 4 | $2,000 | $480 | +$6 |
| Other 7 scenarios | — | 0 | — | — | +$123 |
| **Total** | — | **66** | **$33,000+** | **$14,700+** | **-$520** |

**PPA = $14,700 / $520 ≈ 28x**

Every dollar lost in actual trading was offset by $28 of capital that never entered the market during a crash. CrossMind's refusal engine is not a conservative drag on performance — it is the primary source of risk-adjusted value.
