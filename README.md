# CrossMind

**A red-teamed transparent trading agent that proves when refusing to trade protects capital.**

*Built with Kraken CLI for execution and a verifiable Trust Ledger for auditability.*

| Metric | Result |
|--------|--------|
| Crisis scenarios survived | **3/3** |
| Estimated loss avoided by refusals | **$17.30** |
| Trust Ledger integrity | **SHA-256 chain valid** |
| Gatekeeper score | **77/100** |

> CrossMind survived the 2024 Japan Carry Trade Unwind (BTC -24%), the Iran-Israel Tensions (-13%), and the 2025 Tariff Scare (-13%) — refusing 2 unsafe trades and saving capital in the process.

## The Problem

73% of AI trading bots fail within 6 months. Nobody asks: **"When should this bot NOT trade?"**

## The Solution

CrossMind answers that question through a 4-phase pipeline:

```
War Room → Gatekeeper → Live Execution → Trust Ledger
```

### Phase 1: War Room (Adversarial Stress Testing)
Strategies are stress-tested against real market crashes:
- 2024-08: Japan Carry Trade Unwind (-24%)
- 2024-04: Iran-Israel Tensions (-13%)
- 2025-02: Tariff Scare (-13%)

Strategies that fail are killed. Only survivors proceed.

### Phase 2: Gatekeeper (Survival Scoring)
Surviving strategies are scored on:
- Maximum drawdown (must be < 5%)
- Survival rate across scenarios (must be > 75%)
- Risk-adjusted performance

### Phase 3: Live Execution (Kraken CLI Paper Trading)
Approved strategies trade with real market data via Kraken CLI:
- Paper trading mode (no real money at risk)
- Dead Man's Switch auto-cancels orders if agent crashes
- Slippage modeling (7 bps normal, 200 bps during crashes)

### Phase 4: Trust Ledger (Verifiable Proof)
Every action is recorded with 5 artifacts:
1. **Trade Intent** — what the agent wanted to do
2. **Risk Check** — risk evaluation results
3. **Decision** — EXECUTE or REFUSE
4. **Result** — execution outcome (if traded)
5. **Refusal Proof** — detailed explanation (if refused)

Each entry is SHA-256 hashed and chained to the previous entry, creating a tamper-evident audit trail.

### Refusal Impact Score
After each refusal, CrossMind tracks what would have happened:
> "This refusal saved an estimated $2,340 in potential losses."

## 4-Agent Architecture

| Agent | Type | Role |
|-------|------|------|
| Analyst | Deterministic | RSI calculation, market indicators |
| Strategist | Deterministic | Trade signal generation (mean reversion) |
| Risk Manager | LLM-powered | Approve/refuse trades with reasoning |
| Adversary | LLM-powered | Red team: finds strategy weaknesses |

## Built With

- **Kraken CLI** — AI-native trading infrastructure (paper trading, Dead Man's Switch, WebSocket streaming)
- **Python** — Core trading logic and orchestration
- **SHA-256** — Hash chain for Trust Ledger integrity

## Key Kraken CLI Features Used

| Feature | Purpose |
|---------|---------|
| `kraken paper` | Safe strategy testing with live prices |
| `kraken order cancel-after` | Dead Man's Switch protection |
| `kraken ohlc` | Historical data for War Room replay |
| `kraken ticker` | Real-time price data |
| `kraken mcp` | Native AI agent integration |

## Quick Start

```bash
# Install Kraken CLI
curl --proto '=https' --tlsv1.2 -LsSf https://github.com/krakenfx/kraken-cli/releases/latest/download/kraken-cli-installer.sh | sh

# Initialize paper trading
kraken paper init

# Run full pipeline
python3 run_full_pipeline.py --iterations 5 --interval 30

# Run War Room only
python3 war_room.py

# Launch dashboard
streamlit run dashboard.py
```

## Trading Parameters

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| RSI Period | 14 | Standard, well-tested |
| Entry Threshold | RSI < 28 | Strict oversold (not 30) |
| Exit Threshold | RSI > 65 | Early profit-taking (not 70) |
| Stop Loss | 3% | 1.5x BTC 4H noise band |
| Take Profit | 5% | 1.67 risk-reward ratio |
| Max Drawdown | 5% | Circuit breaker |
| Max Consecutive Losses | 3 | Trading pause |
| Position Size | 10% of capital | Conservative |

## License

MIT

## Author

Barbara Wu — AI Trading Agents Hackathon (lablab.ai), March 2026
