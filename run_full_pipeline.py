"""CrossMind Full Pipeline — End-to-end integration test.

Runs: War Room → Gatekeeper → Live Paper Trading → Summary
This is the main entry point for the complete system.
"""

import json
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from war_room import WarRoom
from gatekeeper import Gatekeeper
from orchestrator import Orchestrator
from adversary import AdversaryAgent


def run_full_pipeline(live_iterations: int = 5, live_interval: int = 30):
    """Run the complete CrossMind pipeline.

    Phase 1: War Room — stress test with historical crashes
    Phase 2: Gatekeeper — evaluate survival fitness
    Phase 3: Adversary — select targeted attack (if Claude available)
    Phase 4: Live Paper Trading — if strategy passes Gatekeeper
    """

    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║                    CrossMind                         ║")
    print("  ║  Red-Teamed Transparent Trading Agent                ║")
    print("  ║  'Proves when it refuses to trade — and why.'       ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    # ============================================================
    # Phase 1: War Room
    # ============================================================
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  PHASE 1: WAR ROOM — Adversarial Stress Testing     │")
    print("  └─────────────────────────────────────────────────────┘")

    war_room = WarRoom()
    results = war_room.run_all_scenarios()

    # Save results for dashboard
    os.makedirs("war_room_cache", exist_ok=True)
    with open("war_room_cache/results.json", "w") as f:
        json.dump(results, f, indent=2)

    # ============================================================
    # Phase 2: Gatekeeper
    # ============================================================
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  PHASE 2: GATEKEEPER — Survival Evaluation          │")
    print("  └─────────────────────────────────────────────────────┘")

    gatekeeper = Gatekeeper()
    verdict = gatekeeper.evaluate(results)

    print(f"\n  Gatekeeper Verdict:")
    print(f"  {'✅ PASSED' if verdict.passed else '❌ FAILED'}")
    print(f"  Score: {verdict.score}/100")
    print(f"  Max Drawdown: {verdict.max_drawdown}%")
    print(f"  Survival Rate: {verdict.survival_rate * 100:.0f}%")
    print(f"  Reasoning: {verdict.reasoning}")
    print()

    if not verdict.passed:
        print("  ⛔ Strategy FAILED Gatekeeper. Not cleared for live trading.")
        print("  Returning to War Room for further training...")
        return {
            "phase": "gatekeeper_failed",
            "verdict": verdict.__dict__,
            "war_room_results": results,
        }

    # ============================================================
    # Phase 3: Adversary Agent
    # ============================================================
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  PHASE 3: ADVERSARY — Red Team Assessment           │")
    print("  └─────────────────────────────────────────────────────┘")

    adversary = AdversaryAgent()
    # Get strategy state from last war room result
    last_result = results[-1] if results else {}
    attack_plan = adversary.select_attack(
        strategy_state={
            "capital": last_result.get("final_capital", 10000),
            "drawdown_pct": last_result.get("max_drawdown", 0),
            "consecutive_losses": 0,
            "win_rate": last_result.get("win_rate", 0),
            "total_trades": last_result.get("total_trades", 0),
        },
        trade_history=[],
        available_scenarios=[r.get("scenario", "") for r in results],
    )

    print(f"\n  Adversary's Attack Plan:")
    print(f"  Target: {attack_plan.get('selected_scenario', 'unknown')}")
    print(f"  Weakness: {attack_plan.get('weakness_identified', 'unknown')}")
    print(f"  Kill Probability: {attack_plan.get('kill_probability', 0) * 100:.0f}%")
    print()

    # ============================================================
    # Phase 4: Live Paper Trading
    # ============================================================
    print("  ┌─────────────────────────────────────────────────────┐")
    print("  │  PHASE 4: LIVE PAPER TRADING — Strategy Deployed    │")
    print("  └─────────────────────────────────────────────────────┘")

    orch = Orchestrator(mode="live")
    orch.enable_dead_man_switch()
    orch.run_live(
        interval_seconds=live_interval,
        max_iterations=live_iterations,
    )

    # Final summary
    print("\n  ╔══════════════════════════════════════════════════════╗")
    print("  ║              CROSSMIND PIPELINE COMPLETE             ║")
    print("  ╚══════════════════════════════════════════════════════╝")

    ledger_stats = orch.ledger.get_stats()
    print(f"  War Room: {sum(1 for r in results if r.get('survived'))}/{len(results)} survived")
    print(f"  Gatekeeper: {'PASSED' if verdict.passed else 'FAILED'} ({verdict.score}/100)")
    print(f"  Live Trades: {orch.portfolio.total_trades}")
    print(f"  Live Refusals: {ledger_stats['refusals']}")
    print(f"  Trust Ledger: {ledger_stats['total_entries']} entries, chain {'valid' if ledger_stats['chain_valid'] else 'INVALID'}")
    print()

    return {
        "phase": "complete",
        "war_room": results,
        "gatekeeper": verdict.__dict__,
        "adversary": attack_plan,
        "live_trades": orch.portfolio.total_trades,
        "live_refusals": ledger_stats["refusals"],
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CrossMind Full Pipeline")
    parser.add_argument("--iterations", type=int, default=3, help="Live trading iterations")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between ticks")
    args = parser.parse_args()

    result = run_full_pipeline(
        live_iterations=args.iterations,
        live_interval=args.interval,
    )
