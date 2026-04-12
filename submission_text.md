# CrossMind — lablab.ai Submission Text

## Long Description (max 2000 chars)

CrossMind introduces Proof of Preservation Alpha (PPA) — a new metric that quantifies the economic value of not trading. Where zkML proves execution happened, PPA proves the decision to stay out was correct. Across 11 real market crash scenarios, CrossMind issued 66 intelligent refusals with 100% Refusal Confirmation Rate: every refusal was retrospectively validated by subsequent price decline within the crash window, verified against historical Kraken OHLCV data.

The numbers: $33,000 in notional risk was blocked across 4 crash environments (Japan Carry -24%, March Correction -26%, Terra/LUNA -54%, COVID -54%). Against $520 in realized losses, those refusals shielded $14,700 in capital from adverse exposure — a PPA Ratio of 28x.

A/B test against identical market data and scenarios confirms the advantage:
- CrossMind (5% pos, circuit breakers): 11/11 survived, -$407 PnL, 2.9% worst drawdown
- All-In Bot (50% pos, no guardrails): 10/11 survived, -$2,435 PnL, 23.8% worst drawdown
- Momentum Chaser (30% pos, no LLM): 7/11 survived, -$6,599 PnL, 19.6% worst drawdown

Each strategy's risk profile is intentional — proving that intelligent constraints outperform unconstrained leverage by 6-16x on the same data.

Architecture: four specialized agents collaborate — deterministic Analyst and Strategist for hallucination-free signals, LLM-powered Risk Manager and Adversary for nuanced judgment and red-teaming. A SHA-256 hash-chained Trust Ledger records every decision. Every refusal carries a structured Refusal Impact Score, permanently timestamped.

On-chain: registered as ERC-8004 Agent #12 on Ethereum Sepolia (AgentRegistry 0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3). 246 TradeIntents, 195 validation checkpoints averaging 96/100, HackathonVault allocation claimed. Refusals are verifiable artifacts — not self-reported claims.

CrossMind does not promise profits. It delivers a 28x PPA: $28 of capital protected for every $1 lost.
