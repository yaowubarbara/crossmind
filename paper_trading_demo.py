"""Experimental script — NOT used in the final CrossMind submission pipeline.
Paper Trading with relaxed parameters to generate demo data."""
import sys, os, time, json
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
# Relax thresholds for demo — real deployment would use strict params
config.RSI_BUY_THRESHOLD = 45   # More signals
config.RSI_SELL_THRESHOLD = 55  # Faster exits
config.MAX_DRAWDOWN_PCT = 0.03  # 3% — will actually trigger circuit breaker

from orchestrator import Orchestrator

orch = Orchestrator(mode="live")
orch.enable_dead_man_switch()
print(f"[Demo Mode] RSI buy<{config.RSI_BUY_THRESHOLD}, sell>{config.RSI_SELL_THRESHOLD}, DD limit {config.MAX_DRAWDOWN_PCT*100}%")
orch.run_live(interval_seconds=120, max_iterations=500)  # every 2 min, up to ~17 hours
