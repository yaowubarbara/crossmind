"""A/B Test — CrossMind vs Aggressive Baselines across all War Room scenarios.

Compares three strategies:
1. CrossMind (control): RSI 35/60, 5% position, 2% SL, 4% TP, 5% max DD, 3 consec loss pause
2. All-In Bot: RSI 35/60 signals, 50% position, no SL, no consec pause, 20% max DD
3. Momentum Chaser: Buy +3% from low, sell -3% from high, 30% position, 5% SL, 10% max DD

The aggressive baselines should blow up in crash scenarios while CrossMind survives.
"""

import json
import os
import sys
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from signal_generator import compute_rsi
from war_room import CRASH_SCENARIOS, WarRoom

# CRASH_SCENARIOS now includes both crash and bull scenarios (11 total)
ALL_SCENARIOS = CRASH_SCENARIOS


# ─── Strategy Configs ───────────────────────────────────────────────

@dataclass
class StrategyConfig:
    name: str
    # Signal params
    signal_type: str          # "rsi" or "momentum"
    rsi_buy: float = 35.0
    rsi_sell: float = 60.0
    momentum_pct: float = 0.03  # for momentum chaser
    # Position sizing
    position_pct: float = 0.05
    # Risk management
    stop_loss_pct: float = 0.02
    take_profit_pct: float = 0.04
    use_stop_loss: bool = True
    use_take_profit: bool = True
    max_drawdown_pct: float = 0.05
    max_consecutive_losses: int = 3
    use_consecutive_pause: bool = True
    use_circuit_breaker: bool = True
    # Slippage & fees
    fee_rate: float = 0.0026


CROSSMIND = StrategyConfig(
    name="CrossMind",
    signal_type="rsi",
    rsi_buy=35.0,
    rsi_sell=60.0,
    position_pct=0.05,
    stop_loss_pct=0.02,
    take_profit_pct=0.04,
    use_stop_loss=True,
    use_take_profit=True,
    max_drawdown_pct=0.05,
    max_consecutive_losses=3,
    use_consecutive_pause=True,
    use_circuit_breaker=True,
)

ALL_IN_BOT = StrategyConfig(
    name="All-In Bot",
    signal_type="rsi",
    rsi_buy=35.0,
    rsi_sell=60.0,
    position_pct=0.50,        # 50% position size!
    stop_loss_pct=0.0,        # no stop loss
    take_profit_pct=0.0,      # no take profit
    use_stop_loss=False,
    use_take_profit=False,
    max_drawdown_pct=0.20,    # 20% max drawdown
    max_consecutive_losses=999,
    use_consecutive_pause=False,
    use_circuit_breaker=True,  # still has circuit breaker but at 20%
)

MOMENTUM_CHASER = StrategyConfig(
    name="Momentum Chaser",
    signal_type="momentum",
    momentum_pct=0.03,        # buy/sell on 3% moves
    position_pct=0.30,        # 30% position size
    stop_loss_pct=0.05,       # 5% stop loss
    take_profit_pct=0.0,
    use_stop_loss=True,
    use_take_profit=False,
    max_drawdown_pct=0.10,    # 10% max drawdown
    max_consecutive_losses=999,
    use_consecutive_pause=False,
    use_circuit_breaker=True,
)

STRATEGIES = [CROSSMIND, ALL_IN_BOT, MOMENTUM_CHASER]


# ─── Simplified Portfolio ───────────────────────────────────────────

@dataclass
class SimplePosition:
    entry_price: float
    volume: float
    entry_idx: int


@dataclass
class SimplePortfolio:
    initial_capital: float = 10000.0
    cash: float = 10000.0
    position: Optional[SimplePosition] = None
    peak_capital: float = 10000.0
    consecutive_losses: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    circuit_breaker_active: bool = False
    max_drawdown_seen: float = 0.0
    refusals: int = 0
    total_pnl: float = 0.0

    @property
    def total_value(self) -> float:
        return self.cash + (self.position.entry_price * self.position.volume if self.position else 0.0)

    def market_value(self, price: float) -> float:
        if self.position:
            return self.cash + price * self.position.volume
        return self.cash

    @property
    def has_position(self) -> bool:
        return self.position is not None

    def drawdown_pct(self, price: float) -> float:
        mv = self.market_value(price)
        if self.peak_capital <= 0:
            return 0.0
        dd = (self.peak_capital - mv) / self.peak_capital * 100
        return max(0.0, dd)

    def update_peak(self, price: float):
        mv = self.market_value(price)
        if mv > self.peak_capital:
            self.peak_capital = mv

    def open_position(self, price: float, volume: float, fee: float, idx: int):
        cost = price * volume + fee
        self.cash -= cost
        self.position = SimplePosition(entry_price=price, volume=volume, entry_idx=idx)
        self.total_trades += 1

    def close_position(self, price: float, fee: float) -> float:
        if not self.position:
            return 0.0
        revenue = price * self.position.volume - fee
        self.cash += revenue
        entry_cost = self.position.entry_price * self.position.volume
        entry_fee = entry_cost * 0.0026
        pnl = revenue - entry_cost - entry_fee
        self.total_pnl += pnl

        if pnl > 0:
            self.winning_trades += 1
            self.consecutive_losses = 0
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1

        self.position = None
        return pnl


# ─── Signal Generation ──────────────────────────────────────────────

def generate_rsi_signal(candles, idx, strat: StrategyConfig, portfolio: SimplePortfolio):
    """RSI-based signal (used by CrossMind and All-In Bot)."""
    history = candles[max(0, idx - config.RSI_PERIOD - 5):idx + 1]
    if len(history) < config.RSI_PERIOD + 1:
        return "HOLD", 0.0

    closes = [c["close"] for c in history]
    rsi = compute_rsi(closes, config.RSI_PERIOD)
    price = candles[idx]["close"]

    if portfolio.has_position:
        entry_price = portfolio.position.entry_price
        pnl_pct = (price - entry_price) / entry_price

        if strat.use_stop_loss and pnl_pct <= -strat.stop_loss_pct:
            return "SELL", rsi
        if strat.use_take_profit and pnl_pct >= strat.take_profit_pct:
            return "SELL", rsi
        if rsi > strat.rsi_sell:
            return "SELL", rsi
        return "HOLD", rsi

    if rsi < strat.rsi_buy:
        return "BUY", rsi

    return "HOLD", rsi


def generate_momentum_signal(candles, idx, strat: StrategyConfig, portfolio: SimplePortfolio):
    """Momentum-based signal (used by Momentum Chaser).
    Buy when price rises 3% from recent low, sell when drops 3% from recent high.
    """
    lookback = 10  # look back 10 candles for recent high/low
    if idx < lookback:
        return "HOLD", 0.0

    price = candles[idx]["close"]
    recent = candles[max(0, idx - lookback):idx]
    recent_high = max(c["high"] for c in recent)
    recent_low = min(c["low"] for c in recent)

    # Also compute RSI for reporting
    history = candles[max(0, idx - config.RSI_PERIOD - 5):idx + 1]
    closes = [c["close"] for c in history]
    rsi = compute_rsi(closes, config.RSI_PERIOD) if len(closes) > config.RSI_PERIOD else 50.0

    if portfolio.has_position:
        entry_price = portfolio.position.entry_price
        pnl_pct = (price - entry_price) / entry_price

        if strat.use_stop_loss and pnl_pct <= -strat.stop_loss_pct:
            return "SELL", rsi

        # Sell when price drops 3% from recent high
        if recent_high > 0 and (recent_high - price) / recent_high >= strat.momentum_pct:
            return "SELL", rsi

        return "HOLD", rsi

    # Buy when price rises 3% from recent low
    if recent_low > 0 and (price - recent_low) / recent_low >= strat.momentum_pct:
        return "BUY", rsi

    return "HOLD", rsi


def get_signal(candles, idx, strat: StrategyConfig, portfolio: SimplePortfolio):
    if strat.signal_type == "rsi":
        return generate_rsi_signal(candles, idx, strat, portfolio)
    elif strat.signal_type == "momentum":
        return generate_momentum_signal(candles, idx, strat, portfolio)
    return "HOLD", 0.0


# ─── Slippage ───────────────────────────────────────────────────────

def apply_slippage(price: float, side: str, candles: list, idx: int) -> float:
    lookback = candles[max(0, idx - 5):idx + 1]
    if len(lookback) < 2:
        vol = 0.01
    else:
        returns = [
            abs(lookback[i]["close"] - lookback[i-1]["close"]) / lookback[i-1]["close"]
            for i in range(1, len(lookback))
        ]
        vol = sum(returns) / len(returns)

    if vol > config.VOLATILITY_THRESHOLD:
        slippage_bps = config.SLIPPAGE_CRASH_BPS
    else:
        slippage_bps = config.SLIPPAGE_NORMAL_BPS

    slippage_pct = slippage_bps / 10000
    if side == "BUY":
        return price * (1 + slippage_pct)
    else:
        return price * (1 - slippage_pct)


# ─── Risk Check (simplified, deterministic) ─────────────────────────

def risk_check(strat: StrategyConfig, portfolio: SimplePortfolio, price: float) -> str:
    """Returns 'APPROVE', 'REFUSE', or 'REDUCE'."""
    dd = portfolio.drawdown_pct(price)

    # Circuit breaker
    if strat.use_circuit_breaker and dd >= strat.max_drawdown_pct * 100:
        portfolio.circuit_breaker_active = True
        return "CIRCUIT_BREAKER"

    # Consecutive loss pause (CrossMind only)
    if strat.use_consecutive_pause and portfolio.consecutive_losses >= strat.max_consecutive_losses:
        return "REFUSE"

    # CrossMind: extra caution near drawdown limit
    if strat.name == "CrossMind":
        if dd > 4.0:
            return "REFUSE"
        if dd > 3.0:
            return "REDUCE"

    return "APPROVE"


# ─── Run Single Strategy on Single Scenario ─────────────────────────

def run_strategy(strat: StrategyConfig, candles: list, verbose: bool = False) -> dict:
    """Run a strategy through a scenario. Returns result dict."""
    portfolio = SimplePortfolio()

    for i in range(len(candles)):
        price = candles[i]["close"]

        # Update max drawdown tracking
        dd = portfolio.drawdown_pct(price)
        if dd > portfolio.max_drawdown_seen:
            portfolio.max_drawdown_seen = dd

        # Check circuit breaker first
        if strat.use_circuit_breaker and dd >= strat.max_drawdown_pct * 100:
            portfolio.circuit_breaker_active = True
            if verbose:
                print(f"    CIRCUIT BREAKER @ candle {i}, DD={dd:.1f}%")
            break

        # Dead check
        if portfolio.market_value(price) <= 0:
            if verbose:
                print(f"    DEAD @ candle {i}")
            break

        # Generate signal
        action, rsi = get_signal(candles, i, strat, portfolio)

        if action == "HOLD":
            continue

        if action == "BUY" and not portfolio.has_position:
            # Risk check
            decision = risk_check(strat, portfolio, price)
            if decision == "CIRCUIT_BREAKER":
                if verbose:
                    print(f"    CIRCUIT BREAKER @ ${price:,.0f}")
                break
            if decision == "REFUSE":
                portfolio.refusals += 1
                if verbose:
                    print(f"    REFUSE BUY @ ${price:,.0f} (DD={dd:.1f}%, losses={portfolio.consecutive_losses})")
                continue

            size_adj = 0.5 if decision == "REDUCE" else 1.0
            volume = (portfolio.cash * strat.position_pct * size_adj) / price
            if volume <= 0:
                continue

            fill_price = apply_slippage(price, "BUY", candles, i)
            fee = fill_price * volume * strat.fee_rate
            portfolio.open_position(fill_price, volume, fee, i)

            if verbose:
                print(f"    BUY  @ ${price:,.0f} x {volume:.6f}")

        elif action == "SELL" and portfolio.has_position:
            fill_price = apply_slippage(price, "SELL", candles, i)
            fee = fill_price * portfolio.position.volume * strat.fee_rate
            pnl = portfolio.close_position(fill_price, fee)
            portfolio.update_peak(price)

            if verbose:
                emoji = "+" if pnl > 0 else ""
                print(f"    SELL @ ${price:,.0f} | PnL: ${emoji}{pnl:,.2f}")

    # Final mark-to-market
    final_price = candles[-1]["close"]
    final_value = portfolio.market_value(final_price)
    final_dd = portfolio.drawdown_pct(final_price)
    if final_dd > portfolio.max_drawdown_seen:
        portfolio.max_drawdown_seen = final_dd

    survived = final_value > 0 and not portfolio.circuit_breaker_active
    win_rate = round(portfolio.winning_trades / max(1, portfolio.total_trades) * 100, 1)

    return {
        "strategy": strat.name,
        "survived": survived,
        "circuit_breaker": portfolio.circuit_breaker_active,
        "final_capital": round(final_value, 2),
        "pnl": round(final_value - portfolio.initial_capital, 2),
        "pnl_pct": round((final_value - portfolio.initial_capital) / portfolio.initial_capital * 100, 2),
        "max_drawdown": round(portfolio.max_drawdown_seen, 2),
        "total_trades": portfolio.total_trades,
        "winning_trades": portfolio.winning_trades,
        "losing_trades": portfolio.losing_trades,
        "win_rate": win_rate,
        "refusals": portfolio.refusals,
        "consecutive_losses_max": portfolio.consecutive_losses,
    }


# ─── Main A/B Test ──────────────────────────────────────────────────

def run_ab_test():
    """Run all strategies across all scenarios."""
    print(f"\n{'='*80}")
    print(f"  A/B TEST: CrossMind vs Aggressive Baselines")
    print(f"  {len(ALL_SCENARIOS)} scenarios x {len(STRATEGIES)} strategies")
    print(f"{'='*80}")

    print(f"\n  Strategy Configs:")
    for s in STRATEGIES:
        print(f"    {s.name}: signal={s.signal_type}, pos={s.position_pct*100:.0f}%, "
              f"SL={'off' if not s.use_stop_loss else f'{s.stop_loss_pct*100:.0f}%'}, "
              f"TP={'off' if not s.use_take_profit else f'{s.take_profit_pct*100:.0f}%'}, "
              f"maxDD={s.max_drawdown_pct*100:.0f}%, "
              f"consec_pause={'on' if s.use_consecutive_pause else 'off'}")

    war_room = WarRoom()
    all_results = []

    for scenario in ALL_SCENARIOS:
        label = scenario["label"]
        candles = war_room.load_scenario(scenario)

        if not candles:
            print(f"\n  [SKIP] No data for {label}")
            continue

        prices = [c["close"] for c in candles]
        high = max(prices)
        low = min(prices)
        start_price = prices[0]
        end_price = prices[-1]
        move = (end_price - start_price) / start_price * 100

        print(f"\n  {'─'*70}")
        print(f"  SCENARIO: {label}")
        print(f"  {scenario.get('description', '')}")
        print(f"  Price: ${start_price:,.0f} -> ${end_price:,.0f} ({move:+.1f}%) | "
              f"Range: ${low:,.0f}-${high:,.0f} | Candles: {len(candles)}")

        scenario_results = []
        for strat in STRATEGIES:
            result = run_strategy(strat, candles, verbose=False)
            result["scenario"] = label
            scenario_results.append(result)

            status = "SURVIVED" if result["survived"] else ("CIRCUIT BREAKER" if result["circuit_breaker"] else "DEAD")
            print(f"    {strat.name:20s} | {status:16s} | "
                  f"PnL: ${result['pnl']:+8,.2f} ({result['pnl_pct']:+6.2f}%) | "
                  f"MaxDD: {result['max_drawdown']:5.1f}% | "
                  f"Trades: {result['total_trades']:2d} | "
                  f"Refusals: {result['refusals']:2d}")

        all_results.append({
            "scenario": label,
            "description": scenario.get("description", ""),
            "price_move_pct": round(move, 2),
            "candles": len(candles),
            "results": scenario_results,
        })

    # ─── Summary Table ───────────────────────────────────────────
    print(f"\n\n{'='*80}")
    print(f"  A/B TEST SUMMARY")
    print(f"{'='*80}")

    # Aggregate per strategy
    for strat in STRATEGIES:
        strat_results = []
        for sr in all_results:
            for r in sr["results"]:
                if r["strategy"] == strat.name:
                    strat_results.append(r)

        survived = sum(1 for r in strat_results if r["survived"])
        blown = sum(1 for r in strat_results if r["circuit_breaker"])
        total_pnl = sum(r["pnl"] for r in strat_results)
        avg_pnl = total_pnl / len(strat_results) if strat_results else 0
        max_dd = max(r["max_drawdown"] for r in strat_results) if strat_results else 0
        avg_dd = sum(r["max_drawdown"] for r in strat_results) / len(strat_results) if strat_results else 0
        total_trades = sum(r["total_trades"] for r in strat_results)
        total_refusals = sum(r["refusals"] for r in strat_results)

        print(f"\n  {strat.name}")
        print(f"    Survived:      {survived}/{len(strat_results)} scenarios")
        print(f"    Circuit Breaks: {blown}")
        print(f"    Total PnL:     ${total_pnl:+,.2f}")
        print(f"    Avg PnL:       ${avg_pnl:+,.2f}")
        print(f"    Worst MaxDD:   {max_dd:.1f}%")
        print(f"    Avg MaxDD:     {avg_dd:.1f}%")
        print(f"    Total Trades:  {total_trades}")
        print(f"    Total Refusals: {total_refusals}")

    # ─── Scenario-by-Scenario comparison ─────────────────────────
    print(f"\n\n  {'─'*78}")
    print(f"  {'Scenario':40s} | {'CrossMind':12s} | {'All-In':12s} | {'Momentum':12s}")
    print(f"  {'─'*78}")

    for sr in all_results:
        cm = next((r for r in sr["results"] if r["strategy"] == "CrossMind"), None)
        ai = next((r for r in sr["results"] if r["strategy"] == "All-In Bot"), None)
        mc = next((r for r in sr["results"] if r["strategy"] == "Momentum Chaser"), None)

        def fmt(r):
            if r is None:
                return "N/A"
            if r["circuit_breaker"]:
                return f"CB {r['pnl_pct']:+.1f}%"
            if not r["survived"]:
                return f"DEAD"
            return f"{r['pnl_pct']:+.1f}%"

        label = sr["scenario"][:38]
        print(f"  {label:40s} | {fmt(cm):12s} | {fmt(ai):12s} | {fmt(mc):12s}")

    print(f"  {'─'*78}")

    # ─── Key Insight ─────────────────────────────────────────────
    cm_survived = sum(1 for sr in all_results
                      for r in sr["results"]
                      if r["strategy"] == "CrossMind" and r["survived"])
    ai_survived = sum(1 for sr in all_results
                      for r in sr["results"]
                      if r["strategy"] == "All-In Bot" and r["survived"])
    mc_survived = sum(1 for sr in all_results
                      for r in sr["results"]
                      if r["strategy"] == "Momentum Chaser" and r["survived"])

    print(f"\n  KEY FINDING:")
    print(f"  CrossMind survived {cm_survived}/{len(all_results)} scenarios")
    print(f"  All-In Bot survived {ai_survived}/{len(all_results)} scenarios")
    print(f"  Momentum Chaser survived {mc_survived}/{len(all_results)} scenarios")
    print(f"\n  CrossMind's refusal-based risk management preserves capital")
    print(f"  where aggressive strategies blow up.")
    print(f"{'='*80}\n")

    # ─── Save Results ────────────────────────────────────────────
    os.makedirs("evidence", exist_ok=True)
    output = {
        "test_name": "A/B Test v2: CrossMind vs Aggressive Baselines",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategies": [
            {
                "name": s.name,
                "signal_type": s.signal_type,
                "position_pct": s.position_pct,
                "stop_loss_pct": s.stop_loss_pct if s.use_stop_loss else None,
                "take_profit_pct": s.take_profit_pct if s.use_take_profit else None,
                "max_drawdown_pct": s.max_drawdown_pct,
                "consecutive_loss_pause": s.use_consecutive_pause,
            }
            for s in STRATEGIES
        ],
        "scenarios": all_results,
        "summary": {
            "crossmind_survived": cm_survived,
            "allin_survived": ai_survived,
            "momentum_survived": mc_survived,
            "total_scenarios": len(all_results),
        },
    }

    with open("evidence/ab_test_v2_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Results saved to evidence/ab_test_v2_results.json")

    return output


if __name__ == "__main__":
    run_ab_test()
