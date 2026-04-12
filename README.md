# CrossMind

**A red-teamed capital protection agent that proves when refusing to trade saves money — and shows you exactly how much.**

> Most AI trading bots optimize for profit. CrossMind optimizes for survival first, profit second.

[**Live Dashboard**](https://huggingface.co/spaces/barbarawu/crossmind-dashboard) · [**ERC-8004 Agent #12**](https://sepolia.etherscan.io/address/0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3) · [**Trust Ledger**](trust_ledger/) · [**Agent Card**](.well-known/agent.json)

---

## Results

| Metric | Result |
|--------|--------|
| Crisis scenarios survived | **11/11** (9 crashes + 2 bull markets) |
| Max drawdown across all scenarios | **2.9%** |
| A/B test vs Momentum Chaser | **CrossMind 11/11 survived, Momentum 7/11 (4 blown)** |
| Trust Ledger integrity | **SHA-256 chain valid + on-chain anchored** |
| ERC-8004 Agent ID | **#12** (Ethereum Sepolia, shared AgentRegistry) |
| On-chain TradeIntents | **246 via RiskRouter** |
| Validation Score | **96/100** (on-chain average, 195 checkpoints) |
| Vault Allocation | **Claimed** (HackathonVault) |
| Refusals | **66 across 11 scenarios** |
| Proof of Preservation Alpha | **28x** ($14,700 protected / $520 actual losses) |
| Refusal Precision | **100%** (all 66 refusals preceded adverse price movement) |
| Total Capital Protected | **$14,700+** across 11 scenarios |

> CrossMind survived 11 market scenarios — 9 crashes including Terra/LUNA (-54%), COVID (-54%), FTX (-30%), and 2 bull markets — while the Momentum Chaser baseline blew up in 4. Max drawdown 2.9% during the worst crypto crash in history.

---

## Proof of Preservation Alpha (PPA)

**PPA measures how much capital CrossMind's refusal decisions protected versus what would have been lost if those trades had executed.**

### Definition

> PPA = Capital Protected by Refusals / Actual Realized Losses

A PPA of 28x means: for every dollar CrossMind actually lost, its refusal engine shielded $28 of capital from entering the market at the worst possible moment.

### Calculation Methodology

For each refused trade, CrossMind records:
1. **Capital at risk** — position size that would have been deployed (5% of $10,000 = $500 per trade)
2. **Market drop during refusal window** — actual price decline over the following 24–72 hours
3. **Capital protected** — capital at risk × market drop percentage
4. **Actual PnL** — realized profit/loss from trades that did execute

PPA is then: `sum(capital_protected) / abs(sum(actual_pnl))`

### Results by Scenario

| Scenario | Market Drop | Refusals | Capital At Risk | Capital Protected | Actual PnL |
|----------|-------------|----------|-----------------|-------------------|------------|
| Terra/LUNA Collapse | -54% | 28 | $14,000 | $7,560 | -$182 |
| COVID Crash | -54% | 16 | $8,000 | $4,320 | -$271 |
| March Correction | -26% | 18 | $9,000 | $2,340 | -$72 |
| Japan Carry Trade | -24% | 4 | $2,000 | $480 | +$6 |
| **Total** | — | **66** | **$33,000+** | **$14,700+** | **-$520** |

**Overall PPA ratio: $14,700 / $520 ≈ 28x**

All 66 refusals preceded adverse price movement (100% refusal precision). CrossMind's refusal engine generated more value through capital protection than it lost in actual trading — across the worst market crashes in crypto history.

---

## The Problem

73% of AI trading bots fail within 6 months. They all answer "when should I trade?" — nobody asks **"when should I NOT trade?"**

## The Solution

CrossMind is a **capital protection system that happens to trade**. Every decision — execution and refusal — produces verifiable validation artifacts recorded in a SHA-256 hash-chained Trust Ledger.

---

## 4-Phase Pipeline

```
War Room → Gatekeeper → Live Execution → Trust Ledger
```

### Phase 1: War Room — Adversarial Stress Testing
Strategies are stress-tested against 11 real historical scenarios (9 crashes + 2 bull markets) using Kraken OHLC data. An LLM-powered Adversary Agent selects the most lethal attack scenarios. Strategies that fail are killed. Only survivors proceed.

### A/B Stress Test — Survival Comparison
CrossMind was tested head-to-head against two aggressive baselines across all 11 scenarios:

| Strategy | Survived | Circuit Breaks | Total PnL | Worst MaxDD |
|----------|----------|---------------|-----------|-------------|
| **CrossMind** | **11/11** | **0** | -$407 | **2.9%** |
| All-In Bot | 10/11 | 1 | -$2,435 | 23.8% |
| Momentum Chaser | 7/11 | 4 | -$6,599 | 19.6% |

Same market data. Same time periods. Only the risk parameters differ. CrossMind's multi-layer risk management is the difference between survival and ruin.

### Phase 2: Gatekeeper — Survival Scoring
Surviving strategies are scored on maximum drawdown (<5%), survival rate (>75%), and risk-adjusted performance. Only strategies that pass the Gatekeeper are cleared for live trading.

### Phase 3: Live Execution — Kraken CLI Paper Trading
Approved strategies trade with real market data via **Kraken CLI**:
- Paper trading sandbox for safe iteration
- Dead Man's Switch (`cancel-after 60`) auto-cancels orders if agent crashes
- Slippage modeling (7 bps normal, 200 bps during crashes)

### Phase 4: Trust Ledger — Verifiable Validation Artifacts
Every action is recorded with 5 fields:
1. **Trade Intent** — what the agent wanted to do
2. **Risk Check** — risk evaluation results
3. **Decision** — EXECUTE or REFUSE
4. **Result** — execution outcome (if traded)
5. **Refusal Proof** — detailed reasoning (if refused)

Each entry is SHA-256 hashed and chained to the previous entry. Click **"Verify Hash Chain Integrity"** on the dashboard to validate.

### Refusal Impact Score
After each refusal, CrossMind tracks what would have happened if the trade had executed, calculating an estimated savings amount.

---

## Autonomous Decision Loop

Every trade decision — including refusals — is made autonomously by the agent pipeline with zero human intervention:

```
Kraken OHLCV (live/cached)
        │
        ▼
┌─────────────────┐
│  ANALYST        │  RSI(14) calculation → market state
│  (deterministic)│  No LLM. No hallucination.
└────────┬────────┘
         │  market_state, rsi, price
         ▼
┌─────────────────┐
│  STRATEGIST     │  Mean-reversion signal → BUY / HOLD / SELL
│  (deterministic)│  Position size = 5% of capital
└────────┬────────┘
         │  trade_intent
         ▼
┌─────────────────┐
│  RISK MANAGER   │  LLM evaluates: drawdown limits, consecutive
│  (LLM-powered)  │  losses, volatility regime, circuit breakers
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
 EXECUTE    REFUSE ──→ Refusal Proof generated (structured JSON)
    │         │        Refusal Impact Score calculated ex-post
    ▼         ▼
┌────────────────────────────────────────┐
│  SHA-256 HASH-CHAINED TRUST LEDGER     │
│  Every decision appended automatically │
│  prev_hash → entry_hash → next entry   │
└────────────────────────────────────────┘
         │
         ▼
   ERC-8004 on-chain (TradeIntent + ValidationCheckpoint)
```

**What is autonomous (zero human intervention):**
- RSI signal generation and market state classification
- Trade intent construction (pair, action, confidence, position size)
- Risk Manager approve/refuse decision with structured reasoning
- Refusal proof generation and impact score calculation
- Trust Ledger append (SHA-256 hash, chain, file write)
- Circuit breaker triggers (max drawdown 5%, consecutive losses 3)
- Dead Man's Switch (`cancel-after 60`) — auto-cancels if agent crashes

**What requires human action:**
- Initial `python3 run_full_pipeline.py` to start the session
- Kraken paper trading account setup (one-time)
- ERC-8004 on-chain registration (one-time, already done: Agent #12)

---

## ERC-8004 Integration

CrossMind is registered on the **ERC-8004 Identity Registry** on Ethereum Sepolia via a shared AgentRegistry:

| Component | Detail |
|-----------|--------|
| Agent Identity NFT | **#12** on Ethereum Sepolia |
| Shared AgentRegistry | `0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3` |
| Agent Card | [`.well-known/agent.json`](.well-known/agent.json) |
| TradeIntents | 246 via RiskRouter (on-chain) |
| Validation Checkpoints | 195 validation checkpoints recorded on-chain |
| Trust Ledger | SHA-256 chained, anchored on-chain |
| Risk Checks | Every trade intent evaluated before execution |
| Strategy Checkpoints | War Room survival data per scenario |

CrossMind's Trust Ledger entries map directly to ERC-8004 validation artifacts: trade intents, risk checks, and strategy checkpoints are all recorded and verifiable. **246 TradeIntents, 195 validation checkpoints, avg score 96/100.** On-chain data is stored via shared ERC-8004 contracts on Ethereum Sepolia.

---

## 4-Agent Architecture

| Agent | Type | Role |
|-------|------|------|
| **Analyst** | Deterministic | RSI calculation, market state |
| **Strategist** | Deterministic | Trade signal generation (mean reversion) |
| **Risk Manager** | LLM-powered | Approve/refuse trades with structured reasoning |
| **Adversary** | LLM-powered | Red team: selects attack scenarios, finds weaknesses |

**Design choice**: Deterministic signals + AI risk judgment. The signal layer is fast, reliable, and hallucination-free. The AI layer handles nuanced risk assessment and generates natural language refusal proofs.

---

## Built With

| Technology | Purpose |
|------------|---------|
| **Kraken CLI** | AI-native trading infrastructure (paper trading, Dead Man's Switch, WebSocket, MCP) |
| **ERC-8004** | On-chain agent identity, reputation, and validation artifacts |
| **ERC-8004 shared contracts** | Ethereum Sepolia (AgentRegistry, RiskRouter, ValidationLog) |
| **Python** | Core trading logic, orchestration, and dashboard |
| **Streamlit** | Intelligence terminal dashboard |
| **SHA-256** | Hash chain for Trust Ledger integrity |

### Kraken CLI Features Used

| Feature | Purpose |
|---------|---------|
| `kraken paper` | Safe strategy testing with live prices |
| `kraken order cancel-after` | Dead Man's Switch protection |
| `kraken ohlc` | Historical data for War Room replay |
| `kraken ticker` | Real-time price data |
| `kraken mcp` | Native AI agent integration |

---

## Risk Parameters

| Parameter | Value |
|-----------|-------|
| Max Drawdown | 5% (circuit breaker) |
| Max Consecutive Losses | 3 (trading pause) |
| Position Size | 5% of capital |
| Stop Loss / Take Profit | 2% / 4% |
| RSI Entry / Exit | < 35 / > 60 |
| Weekend Trading | Blocked |
| US Market Open | Blocked |

---

## Quick Start

```bash
# Install Kraken CLI
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh | sh

# Initialize paper trading
kraken paper init

# Run full pipeline (War Room → Gatekeeper → Adversary → Live)
python3 run_full_pipeline.py --iterations 5 --interval 30

# Run War Room stress test only
python3 war_room.py

# Launch dashboard (demo mode)
CROSSMIND_DEMO=true streamlit run dashboard.py

# Register on ERC-8004 (Ethereum Sepolia)
python3 register_8004.py --private-key 0x...
```

---

## Project Structure

```
crossmind/
├── orchestrator.py          # Main trading loop (live + warroom modes)
├── signal_generator.py      # RSI-based signal generation
├── risk_manager.py          # LLM-powered risk evaluation
├── adversary.py             # LLM-powered red team agent
├── trust_ledger.py          # SHA-256 hash-chained audit trail
├── war_room.py              # Historical crash replay engine
├── gatekeeper.py            # Survival scoring
├── portfolio.py             # Capital and position tracking
├── kraken_client.py         # Kraken CLI wrapper
├── dashboard.py             # Streamlit intelligence terminal
├── register_8004.py         # ERC-8004 on-chain registration
├── run_full_pipeline.py     # End-to-end entry point
├── .well-known/agent.json   # ERC-8004 agent card
├── evidence/                # Registration proofs, war room reports
├── trust_ledger/records/    # All decision records (JSONL + JSON)
└── war_room_cache/          # Cached Kraken OHLC crash data
```

## License

MIT

## Author

Barbara Wu — AI Trading Agents Hackathon (lablab.ai + Surge + Kraken), April 2026
