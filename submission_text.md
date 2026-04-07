# CrossMind — lablab.ai Submission Text

## Long Description (max 2000 chars)

CrossMind is a capital protection agent that answers the question most AI trading bots ignore: when should I NOT trade?

We stress-tested CrossMind against 11 real market scenarios — 9 historical crashes including Terra/LUNA (-54%), COVID (-54%), FTX (-30%), Japan Carry Trade (-24%), plus 2 bull markets — and survived all eleven with a maximum drawdown of just 2.9%.

Then we ran an A/B test. Same data, same time periods, three strategies:
- CrossMind: 11/11 survived, 0 circuit breaks, -$407 total PnL, 2.9% worst drawdown
- All-In Bot: 10/11 survived, 1 circuit break, -$2,435 PnL, 23.8% worst drawdown
- Momentum Chaser: 7/11 survived, 4 circuit breaks, -$6,599 PnL, 19.6% worst drawdown

The only difference is risk parameters. CrossMind's multi-layer risk management is the difference between survival and ruin.

The system runs a 4-phase pipeline: War Room adversarial stress testing, Gatekeeper survival scoring, Live Execution via Kraken CLI paper trading, and a Trust Ledger recording every decision as a SHA-256 hash-chained validation artifact. Across 11 scenarios, CrossMind issued 38 refusals — each with structured proof explaining why the trade was too dangerous and a Refusal Impact Score showing capital saved.

CrossMind is registered as ERC-8004 Agent #12 on Ethereum Sepolia (AgentRegistry 0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3). On-chain artifacts include 11 TradeIntents submitted through the RiskRouter, 11 validation checkpoints with an average score of 90/100, and a claimed HackathonVault allocation.

Four specialized agents collaborate: deterministic Analyst and Strategist for hallucination-free signals, and LLM-powered Risk Manager and Adversary for nuanced risk judgment and red-teaming. Built with Kraken CLI (paper trading, Dead Man's Switch, OHLC, MCP), ERC-8004 shared contracts, Python, and Streamlit.

CrossMind does not promise profits. It promises you will still have capital tomorrow.
