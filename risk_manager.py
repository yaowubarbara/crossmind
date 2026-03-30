"""Risk Manager Agent — Claude-powered trade approval/refusal."""

import json
import os
from dataclasses import dataclass
from typing import Optional

import config

try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False


@dataclass
class RiskDecision:
    """Risk Manager's decision on a trade proposal."""
    decision: str           # "APPROVE" or "REFUSE"
    risk_level: str         # "LOW", "MEDIUM", "HIGH", "EXTREME"
    reasoning: str          # Why this decision
    refusal_proof: Optional[str]  # Detailed refusal explanation (if REFUSE)
    position_size_adj: float     # Adjusted position size (0.0 - 1.0)


class RiskManager:
    """Claude-powered Risk Manager Agent.

    Personality: Extremely cautious, always looking for reasons to REFUSE.
    Biased toward capital preservation over profit.
    """

    SYSTEM_PROMPT = """You are CrossMind's Risk Manager — an extremely cautious,
paranoid risk officer for an AI trading system. Your job is to PROTECT CAPITAL,
not to make money. You are naturally suspicious of every trade proposal.

Your personality:
- You ALWAYS look for reasons to refuse a trade
- You care more about NOT LOSING than about WINNING
- You treat every trade as guilty until proven safe
- You write detailed refusal explanations when you reject trades
- You never approve trades near drawdown limits

You evaluate trade proposals against these hard rules:
- Max portfolio drawdown: 5% (circuit breaker)
- Max consecutive losses: 3 (pause trading)
- Max position size: 10% of capital
- No weekend trading
- No trading during US market open (13:30-15:00 UTC)
- If drawdown > 3%, reduce position size by 50%
- If drawdown > 4%, only approve with EXTREME confidence signals

When you REFUSE, write a detailed "refusal proof" explaining:
1. Which specific rule was violated or nearly violated
2. What could go wrong if this trade was executed
3. What conditions need to change before you would approve

You MUST respond using the risk_assessment tool."""

    def __init__(self):
        if HAS_CLAUDE:
            self.client = anthropic.Anthropic()
        else:
            self.client = None

    def evaluate(self, trade_intent: dict, portfolio_state: dict) -> RiskDecision:
        """Evaluate a trade proposal.

        Args:
            trade_intent: {action, pair, price, volume, reason, rsi, confidence}
            portfolio_state: {capital, drawdown_pct, consecutive_losses,
                            open_positions, current_pnl}
        """
        # Hard rule checks first (deterministic, no Claude needed)
        hard_refusal = self._check_hard_rules(trade_intent, portfolio_state)
        if hard_refusal:
            return hard_refusal

        # Claude evaluation for soft judgment
        if self.client:
            return self._claude_evaluate(trade_intent, portfolio_state)
        else:
            return self._fallback_evaluate(trade_intent, portfolio_state)

    def _check_hard_rules(self, intent: dict, state: dict) -> Optional[RiskDecision]:
        """Check deterministic hard rules. Returns refusal if any violated."""
        drawdown = state.get("drawdown_pct", 0)
        consec_losses = state.get("consecutive_losses", 0)

        # Circuit breaker
        if drawdown >= config.MAX_DRAWDOWN_PCT * 100:
            return RiskDecision(
                decision="REFUSE",
                risk_level="EXTREME",
                reasoning=f"CIRCUIT BREAKER: Portfolio drawdown {drawdown:.1f}% "
                          f"has reached {config.MAX_DRAWDOWN_PCT*100}% limit.",
                refusal_proof=f"Circuit breaker triggered. Drawdown {drawdown:.1f}% >= "
                              f"{config.MAX_DRAWDOWN_PCT*100}% threshold. ALL trading "
                              f"suspended until drawdown recovers below "
                              f"{config.MAX_DRAWDOWN_PCT*100 - 2}%. "
                              f"This is a non-negotiable safety mechanism.",
                position_size_adj=0.0,
            )

        # Consecutive loss pause
        if consec_losses >= config.MAX_CONSECUTIVE_LOSSES:
            return RiskDecision(
                decision="REFUSE",
                risk_level="HIGH",
                reasoning=f"LOSS PAUSE: {consec_losses} consecutive losses. "
                          f"Limit is {config.MAX_CONSECUTIVE_LOSSES}.",
                refusal_proof=f"Trading paused after {consec_losses} consecutive losses. "
                              f"Strategy may not suit current market conditions. "
                              f"Wait for market regime change or manual review.",
                position_size_adj=0.0,
            )

        return None

    def _claude_evaluate(self, intent: dict, state: dict) -> RiskDecision:
        """Use Claude for nuanced risk evaluation."""
        message = f"""
TRADE PROPOSAL:
{json.dumps(intent, indent=2)}

PORTFOLIO STATE:
{json.dumps(state, indent=2)}

RISK RULES:
- Max drawdown: {config.MAX_DRAWDOWN_PCT*100}%
- Current drawdown: {state.get('drawdown_pct', 0):.1f}%
- Max consecutive losses: {config.MAX_CONSECUTIVE_LOSSES}
- Current consecutive losses: {state.get('consecutive_losses', 0)}
- Max position size: {config.MAX_POSITION_PCT*100}% of capital

Evaluate this trade. Remember: you are paranoid and biased toward refusal.
"""

        try:
            response = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                tools=[{
                    "name": "risk_assessment",
                    "description": "Submit your risk assessment decision",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "decision": {
                                "type": "string",
                                "enum": ["APPROVE", "REFUSE"]
                            },
                            "risk_level": {
                                "type": "string",
                                "enum": ["LOW", "MEDIUM", "HIGH", "EXTREME"]
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "Brief reasoning for the decision"
                            },
                            "refusal_proof": {
                                "type": "string",
                                "description": "If REFUSE: detailed explanation of why, which rules are at risk, what could go wrong"
                            },
                            "position_size_adjustment": {
                                "type": "number",
                                "description": "Recommended position size as fraction of max (0.0 to 1.0)"
                            }
                        },
                        "required": ["decision", "risk_level", "reasoning", "position_size_adjustment"]
                    }
                }],
                tool_choice={"type": "tool", "name": "risk_assessment"},
                messages=[{"role": "user", "content": message}],
            )

            # Extract tool use response
            for block in response.content:
                if block.type == "tool_use":
                    data = block.input
                    return RiskDecision(
                        decision=data["decision"],
                        risk_level=data["risk_level"],
                        reasoning=data["reasoning"],
                        refusal_proof=data.get("refusal_proof"),
                        position_size_adj=data.get("position_size_adjustment", 1.0),
                    )

        except Exception as e:
            print(f"[Risk Manager] Claude error: {e}. Using fallback.")
            return self._fallback_evaluate(intent, state)

        return self._fallback_evaluate(intent, state)

    def _fallback_evaluate(self, intent: dict, state: dict) -> RiskDecision:
        """Fallback evaluation without Claude."""
        drawdown = state.get("drawdown_pct", 0)

        # Conservative fallback rules
        if drawdown > 4:
            return RiskDecision(
                decision="REFUSE",
                risk_level="HIGH",
                reasoning=f"Drawdown {drawdown:.1f}% approaching limit. Caution.",
                refusal_proof=f"Drawdown at {drawdown:.1f}%, only 1% from circuit breaker. "
                              f"Risk of total trading suspension too high.",
                position_size_adj=0.0,
            )

        if drawdown > 3:
            return RiskDecision(
                decision="APPROVE",
                risk_level="MEDIUM",
                reasoning=f"Elevated drawdown {drawdown:.1f}%. Reducing position.",
                refusal_proof=None,
                position_size_adj=0.5,
            )

        return RiskDecision(
            decision="APPROVE",
            risk_level="LOW",
            reasoning=f"All checks passed. Drawdown {drawdown:.1f}% within limits.",
            refusal_proof=None,
            position_size_adj=1.0,
        )
