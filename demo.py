"""CrossMind One-Click Demo — runs everything judges need to see.

Usage: python3 demo.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║            CrossMind — One-Click Demo                ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()

    # Step 1: War Room
    print("  [1/3] Running War Room stress tests...")
    from war_room import WarRoom
    wr = WarRoom()
    results = wr.run_all_scenarios()

    # Save for dashboard
    os.makedirs("war_room_cache", exist_ok=True)
    with open("war_room_cache/results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Save evidence
    os.makedirs("evidence", exist_ok=True)
    with open("evidence/war_room_report.json", "w") as f:
        json.dump(results, f, indent=2)

    # Step 2: Gatekeeper
    print("\n  [2/3] Running Gatekeeper evaluation...")
    from gatekeeper import Gatekeeper
    gk = Gatekeeper()
    verdict = gk.evaluate(results)
    print(f"  Verdict: {'PASSED' if verdict.passed else 'FAILED'} ({verdict.score}/100)")

    # Step 3: Summary
    print("\n  [3/3] Generating evidence package...")

    # Find refusal proofs
    import glob
    refusal_files = glob.glob("trust_ledger/records/*/2026*refuse*.json")
    if refusal_files:
        with open(refusal_files[0]) as f:
            with open("evidence/sample_refusal_proof.json", "w") as out:
                out.write(f.read())

    # Adversary report
    from adversary import AdversaryAgent
    adv = AdversaryAgent()
    last = results[-1] if results else {}
    attack = adv.select_attack(
        {"capital": last.get("final_capital", 10000), "drawdown_pct": last.get("max_drawdown", 0),
         "consecutive_losses": 0, "win_rate": last.get("win_rate", 0), "total_trades": last.get("total_trades", 0)},
        [], [r.get("scenario", "") for r in results],
    )
    with open("evidence/adversary_attack_report.json", "w") as f:
        json.dump(attack, f, indent=2)

    survived = sum(1 for r in results if r.get("survived"))
    total_refusals = sum(r.get("refusals", 0) for r in results)

    print()
    print("  ╔══════════════════════════════════════════════════════╗")
    print("  ║                  DEMO COMPLETE                       ║")
    print("  ╠══════════════════════════════════════════════════════╣")
    print(f"  ║  War Room:     {survived}/{len(results)} scenarios survived            ║")
    print(f"  ║  Gatekeeper:   {'PASSED' if verdict.passed else 'FAILED'} ({verdict.score}/100)                    ║")
    print(f"  ║  Refusals:     {total_refusals}                                  ║")
    print("  ║                                                      ║")
    print("  ║  Next: streamlit run dashboard.py                    ║")
    print("  ╚══════════════════════════════════════════════════════╝")
    print()


if __name__ == "__main__":
    main()
