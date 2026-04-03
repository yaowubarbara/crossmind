# CrossMind

**A red-teamed capital protection agent that proves when refusing to trade saves money — and shows you exactly how much.**

> Most AI trading bots optimize for profit. CrossMind optimizes for survival first, profit second.

[**Live Dashboard**](https://huggingface.co/spaces/barbarawu/crossmind-dashboard) · [**ERC-8004 Agent #3429**](https://sepolia.basescan.org/tx/0x5ab87e47df96fc2f114d20ff815db6f73c70b111d9e4c599e81a18165074d7e6) · [**Trust Ledger**](trust_ledger/) · [**Agent Card**](.well-known/agent.json)

---

## Results

| Metric | Result |
|--------|--------|
| Crisis scenarios survived | **6/6** |
| Max drawdown during -24% crash | **1.9%** |
| Trust Ledger integrity | **SHA-256 chain valid** |
| Gatekeeper score | **77/100** |
| ERC-8004 Agent ID | **#3429** (Base Sepolia) |
| Refusal rate | **25%** of signals blocked |

> CrossMind survived the 2024 Japan Carry Trade Unwind (BTC -24%), the Iran-Israel Tensions (-13%), the 2025 Tariff Scare (-13%), Year-End Selloff (-43%), March Correction (-26%), and Summer Grind (-18%) — refusing unsafe trades and preserving capital across all six.

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
Strategies are stress-tested against 6 real historical crashes using Kraken OHLC data. An LLM-powered Adversary Agent selects the most lethal attack scenarios. Strategies that fail are killed. Only survivors proceed.

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

## ERC-8004 Integration

CrossMind is registered on the **ERC-8004 Identity Registry** on Base Sepolia:

| Component | Detail |
|-----------|--------|
| Agent Identity NFT | **#3429** on Base Sepolia |
| Registry | `0x8004A818BFB912233c491871b3d84c89A494BD9e` |
| Agent Card | [`.well-known/agent.json`](.well-known/agent.json) |
| Validation Artifacts | Trust Ledger (JSONL, SHA-256 chained) |
| Risk Checks | Every trade intent evaluated before execution |
| Strategy Checkpoints | War Room survival data per scenario |

CrossMind's Trust Ledger entries map directly to ERC-8004 validation artifacts: trade intents, risk checks, and strategy checkpoints are all recorded and verifiable.

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
| Position Size | 10% of capital |
| Stop Loss / Take Profit | 3% / 5% |
| RSI Entry / Exit | < 28 / > 65 |
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

# Register on ERC-8004 (Base Sepolia)
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
