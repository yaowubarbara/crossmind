"""48-Hour Paper Trading Runner.

Runs CrossMind in live paper trading mode for 48 hours,
logging all decisions to Trust Ledger.
Designed to run in background: nohup python3 paper_trading_48h.py &
"""

import sys
import os
import time
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orchestrator import Orchestrator
import config


def run_48h():
    """Run paper trading for 48 hours."""
    duration_hours = 48
    check_interval = 300  # Check every 5 minutes (4H candles don't change fast)
    max_iterations = (duration_hours * 3600) // check_interval

    print(f"[48H Runner] Starting {duration_hours}h paper trading run")
    print(f"[48H Runner] Check interval: {check_interval}s ({check_interval // 60} min)")
    print(f"[48H Runner] Max iterations: {max_iterations}")
    print(f"[48H Runner] Started at: {datetime.now(timezone.utc).isoformat()}")

    # Log to file
    log_file = "paper_trading_48h.log"
    with open(log_file, "a") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"48H Paper Trading Started: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Interval: {check_interval}s, Max iterations: {max_iterations}\n")
        f.write(f"{'='*60}\n")

    orch = Orchestrator(mode="live")
    orch.enable_dead_man_switch()
    orch.run_live(
        interval_seconds=check_interval,
        max_iterations=max_iterations,
    )

    # Save final results
    results = {
        "duration_hours": duration_hours,
        "started": datetime.now(timezone.utc).isoformat(),
        "portfolio": orch.portfolio.to_dict(),
        "ledger_stats": orch.ledger.get_stats(),
        "trade_history": orch.portfolio.trade_history,
    }

    with open("paper_trading_48h_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[48H Runner] Results saved to paper_trading_48h_results.json")


if __name__ == "__main__":
    run_48h()
