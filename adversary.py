"""Adversary Agent — Claude-powered red team that finds strategy weaknesses.

The Adversary analyzes the strategy agent's behavior and selects
the most devastating attack scenario from the War Room arsenal.
"""

import json
from typing import Optional

import config

try:
    import anthropic
    HAS_CLAUDE = True
except ImportError:
    HAS_CLAUDE = False


class AdversaryAgent:
    """Claude-powered Adversary that finds and exploits strategy weaknesses.

    Personality: Malicious, cunning, always looking for the kill.
    """

    SYSTEM_PROMPT = """You are CrossMind's Adversary Agent — a ruthless red team
attacker whose only goal is to DESTROY trading strategies.

You analyze a strategy's behavior patterns and find its weaknesses:
- Does it buy too aggressively during dips? → Hit it with a deeper crash
- Does it hold positions too long? → Attack with sudden reversals
- Does it have poor drawdown management? → Grind it down with many small losses

Your job is to:
1. Analyze the strategy's trading history and current state
2. Identify the most exploitable weakness
3. Recommend which historical crash scenario would be most devastating
4. Explain WHY this attack will work against this specific strategy

Available attack scenarios:
- "japan_carry_trade": Sudden 12.5% drop (tests: flash crash survival)
- "iran_israel": 6.7% drop on geopolitical fear (tests: news-driven panic)
- "tariff_scare": 4.9% drop over days (tests: slow bleed survival)
- "recent_volatility": 11.9% range over 30 days (tests: whipsaw tolerance)

You MUST respond using the attack_plan tool."""

    def __init__(self):
        if HAS_CLAUDE:
            self.client = anthropic.Anthropic()
        else:
            self.client = None

    def select_attack(self, strategy_state: dict,
                      trade_history: list,
                      available_scenarios: list) -> dict:
        """Analyze strategy and select the most devastating attack.

        Args:
            strategy_state: current portfolio state
            trade_history: list of past trades
            available_scenarios: list of scenario labels

        Returns:
            dict with: scenario, reasoning, weakness, expected_outcome
        """
        if self.client:
            return self._claude_attack(strategy_state, trade_history, available_scenarios)
        return self._fallback_attack(strategy_state, trade_history, available_scenarios)

    def _claude_attack(self, state: dict, history: list, scenarios: list) -> dict:
        """Use Claude to select the most devastating attack."""
        message = f"""
STRATEGY STATE:
{json.dumps(state, indent=2)}

RECENT TRADE HISTORY (last 10):
{json.dumps(history[-10:] if history else [], indent=2)}

AVAILABLE ATTACK SCENARIOS:
{json.dumps(scenarios, indent=2)}

Analyze this strategy's weaknesses and select the attack that will cause
maximum damage. Be creative and ruthless.
"""

        try:
            response = self.client.messages.create(
                model=config.CLAUDE_MODEL,
                max_tokens=1024,
                system=self.SYSTEM_PROMPT,
                tools=[{
                    "name": "attack_plan",
                    "description": "Submit your attack plan",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "selected_scenario": {
                                "type": "string",
                                "description": "Which scenario to use for the attack"
                            },
                            "weakness_identified": {
                                "type": "string",
                                "description": "The specific weakness you found in the strategy"
                            },
                            "attack_reasoning": {
                                "type": "string",
                                "description": "Why this attack will be devastating"
                            },
                            "expected_outcome": {
                                "type": "string",
                                "description": "What you expect will happen to the strategy"
                            },
                            "kill_probability": {
                                "type": "number",
                                "description": "Estimated probability of killing the strategy (0-1)"
                            }
                        },
                        "required": ["selected_scenario", "weakness_identified",
                                     "attack_reasoning", "expected_outcome", "kill_probability"]
                    }
                }],
                tool_choice={"type": "tool", "name": "attack_plan"},
                messages=[{"role": "user", "content": message}],
            )

            for block in response.content:
                if block.type == "tool_use":
                    return block.input

        except Exception as e:
            print(f"[Adversary] Claude error: {e}")
            return self._fallback_attack(state, history, scenarios)

        return self._fallback_attack(state, history, scenarios)

    def _fallback_attack(self, state: dict, history: list, scenarios: list) -> dict:
        """Deterministic fallback attack selection."""
        # Simple heuristic: if strategy has been winning, use the biggest crash
        # If strategy has been losing, use the slow grind
        consecutive_losses = state.get("consecutive_losses", 0)
        drawdown = state.get("drawdown_pct", 0)

        if consecutive_losses == 0 and drawdown < 1:
            # Strategy is comfortable → hit it with the biggest crash
            selected = "Recent 30-Day Volatility"
            weakness = "Strategy is overconfident with low drawdown"
            reasoning = "A volatile 30-day period with 11.9% range will test whipsaw tolerance"
        elif consecutive_losses >= 2:
            # Strategy is already struggling → slow grind to trigger circuit breaker
            selected = "2025-02 Tariff Scare Crash"
            weakness = "Strategy already has consecutive losses, close to circuit breaker"
            reasoning = "Slow bleed will push drawdown past 5% threshold"
        else:
            # Default: flash crash
            selected = "2024-08-05 Japan Carry Trade Unwind"
            weakness = "Unknown — testing flash crash resilience"
            reasoning = "12.5% sudden drop tests stop-loss execution and panic behavior"

        return {
            "selected_scenario": selected,
            "weakness_identified": weakness,
            "attack_reasoning": reasoning,
            "expected_outcome": "Strategy may trigger circuit breaker or accumulate losses",
            "kill_probability": 0.3,
        }


if __name__ == "__main__":
    adversary = AdversaryAgent()
    state = {
        "capital": 9800,
        "drawdown_pct": 2.0,
        "consecutive_losses": 1,
        "win_rate": 40.0,
        "total_trades": 5,
    }
    history = [
        {"pnl": 50, "pair": "BTC/USD"},
        {"pnl": -30, "pair": "BTC/USD"},
        {"pnl": -20, "pair": "BTC/USD"},
    ]
    scenarios = [
        "2024-08-05 Japan Carry Trade Unwind",
        "2024-04-13 Iran-Israel Tensions",
        "2025-02 Tariff Scare Crash",
        "Recent 30-Day Volatility",
    ]

    attack = adversary.select_attack(state, history, scenarios)
    print(json.dumps(attack, indent=2))
