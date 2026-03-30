"""Experimental script — NOT used in the final CrossMind submission pipeline.
Multi-pair paper trading with relaxed parameters for data generation testing."""
import sys, os, time, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
# Demo-friendly parameters
config.RSI_BUY_THRESHOLD = 40
config.RSI_SELL_THRESHOLD = 58
config.MAX_DRAWDOWN_PCT = 0.03
config.PAIR = "SOL/USD"
config.PAIR_KRAKEN = "SOLUSD"

from orchestrator import Orchestrator

print(f"[Multi] Pair: {config.PAIR}")
print(f"[Multi] RSI buy<{config.RSI_BUY_THRESHOLD}, sell>{config.RSI_SELL_THRESHOLD}")
print(f"[Multi] Drawdown limit: {config.MAX_DRAWDOWN_PCT*100}%")

orch = Orchestrator(mode="live")
orch.enable_dead_man_switch()
orch.run_live(interval_seconds=120, max_iterations=500)
