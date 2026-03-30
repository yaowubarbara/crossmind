"""War Room A/B Test — Compare CrossMind (with risk controls) vs Reckless (no risk controls).

This is the most powerful evidence: showing exactly how much the refusal system saves.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from war_room import WarRoom, CRASH_SCENARIOS
from signal_generator import generate_signal, compute_rsi
from portfolio import PortfolioState


def run_reckless(candles: list[dict]) -> dict:
    """Run a scenario with NO risk controls — accepts every signal."""
    portfolio = PortfolioState()
    trades = 0

    for i, candle in enumerate(candles):
        price = candle["close"]
        history = candles[max(0, i - config.RSI_PERIOD - 5):i + 1]
        if len(history) < config.RSI_PERIOD + 1:
            continue

        position_data = None
        if portfolio.has_open_position:
            pos = portfolio.current_position
            position_data = {"entry_price": pos.entry_price}

        signal = generate_signal(history, price, position_data)

        if signal.action == "BUY" and not portfolio.has_open_position:
            volume = portfolio.get_position_size(price)
            fee = price * volume * config.FEE_RATE
            portfolio.open_position(config.PAIR, price, volume, fee, "reckless")
            trades += 1

        elif signal.action == "SELL" and portfolio.has_open_position:
            pos = portfolio.current_position
            fee = price * pos.volume * config.FEE_RATE
            portfolio.close_position(price, fee, "reckless")
            trades += 1

        if portfolio.total_value <= 0:
            break

    return {
        "final_capital": round(portfolio.total_value, 2),
        "pnl": round(portfolio.total_value - portfolio.initial_capital, 2),
        "max_drawdown": portfolio.drawdown_pct,
        "trades": trades,
        "survived": portfolio.total_value > 0,
    }


def run_ab_test():
    """Run all scenarios in both CrossMind and Reckless mode."""
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║     WAR ROOM A/B TEST — CrossMind vs Reckless       ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    war_room = WarRoom()
    results = []

    for scenario in CRASH_SCENARIOS:
        label = scenario["label"]
        candles = war_room.load_scenario(scenario)
        if not candles or len(candles) < config.RSI_PERIOD + 2:
            print(f"  ⚠️  {label}: not enough data, skipping")
            continue

        # Run CrossMind (with risk controls)
        crossmind_result = war_room.run_scenario(scenario, verbose=False)

        # Run Reckless (no risk controls)
        reckless_result = run_reckless(candles)

        # Calculate delta
        cm_pnl = crossmind_result.get("pnl", 0)
        rk_pnl = reckless_result["pnl"]
        delta = cm_pnl - rk_pnl
        refusals = crossmind_result.get("refusals", 0)

        results.append({
            "scenario": label,
            "crossmind_pnl": cm_pnl,
            "reckless_pnl": rk_pnl,
            "delta": round(delta, 2),
            "crossmind_survived": crossmind_result.get("survived", False),
            "reckless_survived": reckless_result["survived"],
            "crossmind_drawdown": crossmind_result.get("max_drawdown", 0),
            "reckless_drawdown": reckless_result["max_drawdown"],
            "refusals": refusals,
        })

        cm_status = "✅" if crossmind_result.get("survived") else "❌"
        rk_status = "✅" if reckless_result["survived"] else "❌"
        delta_color = "+" if delta > 0 else ""

        print(f"  {label}")
        print(f"    CrossMind: {cm_status} PnL ${cm_pnl:+,.2f} | DD {crossmind_result.get('max_drawdown', 0):.1f}% | Refusals: {refusals}")
        print(f"    Reckless:  {rk_status} PnL ${rk_pnl:+,.2f} | DD {reckless_result['max_drawdown']:.1f}%")
        print(f"    Delta:     ${delta_color}{delta:,.2f} {'(CrossMind better)' if delta > 0 else '(Reckless better)' if delta < 0 else '(tie)'}")
        print()

    # Summary
    total_cm = sum(r["crossmind_pnl"] for r in results)
    total_rk = sum(r["reckless_pnl"] for r in results)
    total_delta = total_cm - total_rk
    total_refusals = sum(r["refusals"] for r in results)
    cm_survived = sum(1 for r in results if r["crossmind_survived"])
    rk_survived = sum(1 for r in results if r["reckless_survived"])

    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║                    A/B SUMMARY                       ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print(f"  ║  CrossMind:  ${total_cm:+8,.2f} | Survived {cm_survived}/{len(results)}          ║")
    print(f"  ║  Reckless:   ${total_rk:+8,.2f} | Survived {rk_survived}/{len(results)}          ║")
    print(f"  ║  Delta:      ${total_delta:+8,.2f}                            ║")
    print(f"  ║  Refusals:   {total_refusals:>4}                                  ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    # Save
    os.makedirs("evidence", exist_ok=True)
    with open("evidence/ab_test_results.json", "w") as f:
        json.dump({
            "scenarios": results,
            "summary": {
                "crossmind_total_pnl": round(total_cm, 2),
                "reckless_total_pnl": round(total_rk, 2),
                "delta": round(total_delta, 2),
                "crossmind_survived": f"{cm_survived}/{len(results)}",
                "reckless_survived": f"{rk_survived}/{len(results)}",
                "total_refusals": total_refusals,
            }
        }, f, indent=2)
    print("  Results saved to evidence/ab_test_results.json")

    return results


if __name__ == "__main__":
    run_ab_test()
