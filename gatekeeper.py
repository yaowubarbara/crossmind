"""Gatekeeper — evaluates strategy survival after War Room testing.

Only strategies that pass the Gatekeeper's minimum thresholds
are allowed to trade with real (paper) capital.
"""

from dataclasses import dataclass


@dataclass
class GatekeeperVerdict:
    """Gatekeeper's verdict on a strategy."""
    passed: bool
    score: float           # 0-100
    max_drawdown: float
    survival_rate: float   # across scenarios
    refusal_effectiveness: float  # % of refusals that saved money
    reasoning: str


class Gatekeeper:
    """Evaluates strategy survival fitness."""

    # Minimum thresholds to pass
    MIN_SURVIVAL_RATE = 0.75     # Must survive 75% of scenarios
    MAX_ALLOWED_DRAWDOWN = 5.0   # Max drawdown in any scenario
    MIN_REFUSAL_RATE = 0.1       # Must refuse at least 10% of signals

    def evaluate(self, war_room_results: list[dict]) -> GatekeeperVerdict:
        """Evaluate a strategy based on War Room results.

        Args:
            war_room_results: list of results from WarRoom.run_scenario()

        Returns:
            GatekeeperVerdict with pass/fail and score
        """
        if not war_room_results:
            return GatekeeperVerdict(
                passed=False, score=0, max_drawdown=0,
                survival_rate=0, refusal_effectiveness=0,
                reasoning="No War Room data available",
            )

        total = len(war_room_results)
        survived = sum(1 for r in war_room_results if r.get("survived", False))
        survival_rate = survived / total

        max_dd = max(r.get("max_drawdown", 0) for r in war_room_results)
        total_refusals = sum(r.get("refusals", 0) for r in war_room_results)
        total_entries = sum(
            r.get("total_trades", 0) + r.get("refusals", 0)
            for r in war_room_results
        )
        refusal_rate = total_refusals / max(1, total_entries)

        avg_pnl = sum(r.get("pnl", 0) for r in war_room_results) / total

        # Calculate score (0-100)
        score = 0
        score += min(40, survival_rate * 40)          # 40 pts for survival
        score += min(30, max(0, 30 - max_dd * 6))     # 30 pts for low drawdown
        score += min(15, refusal_rate * 100)           # 15 pts for refusals
        score += min(15, max(0, avg_pnl / 10 + 7.5))  # 15 pts for PnL

        # Pass/fail
        reasons = []
        passed = True

        if survival_rate < self.MIN_SURVIVAL_RATE:
            passed = False
            reasons.append(f"Survival rate {survival_rate*100:.0f}% < {self.MIN_SURVIVAL_RATE*100:.0f}%")

        if max_dd > self.MAX_ALLOWED_DRAWDOWN:
            passed = False
            reasons.append(f"Max drawdown {max_dd:.1f}% > {self.MAX_ALLOWED_DRAWDOWN:.1f}%")

        if refusal_rate < self.MIN_REFUSAL_RATE and total_entries > 5:
            reasons.append(f"Warning: refusal rate {refusal_rate*100:.0f}% < {self.MIN_REFUSAL_RATE*100:.0f}% (not blocking)")

        if passed:
            reasons.append(f"Strategy passed all thresholds. Score: {score:.0f}/100")

        return GatekeeperVerdict(
            passed=passed,
            score=round(score, 1),
            max_drawdown=max_dd,
            survival_rate=round(survival_rate, 2),
            refusal_effectiveness=round(refusal_rate, 2),
            reasoning=" | ".join(reasons),
        )


if __name__ == "__main__":
    # Test with sample results
    sample_results = [
        {"survived": True, "max_drawdown": 0.0, "pnl": 0, "total_trades": 0, "refusals": 0},
        {"survived": True, "max_drawdown": 0.0, "pnl": 0, "total_trades": 0, "refusals": 0},
        {"survived": True, "max_drawdown": 0.0, "pnl": 0, "total_trades": 0, "refusals": 0},
        {"survived": True, "max_drawdown": 0.4, "pnl": -40.93, "total_trades": 2, "refusals": 0},
    ]

    gk = Gatekeeper()
    verdict = gk.evaluate(sample_results)
    print(f"Passed: {verdict.passed}")
    print(f"Score: {verdict.score}/100")
    print(f"Reasoning: {verdict.reasoning}")
