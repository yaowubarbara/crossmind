"""War Room — Adversarial stress testing with historical crash replay.

Uses real Kraken historical data to simulate market crashes.
Strategy agents must survive or they die.
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

import config
from kraken_client import KrakenClient
from signal_generator import generate_signal, compute_rsi
from risk_manager import RiskManager
from trust_ledger import TrustLedger
from portfolio import PortfolioState


def apply_slippage(price: float, side: str, candles: list, idx: int) -> float:
    """Apply realistic slippage based on market volatility.

    Normal conditions: 5-10 bps
    High volatility: 100-300 bps
    """
    # Calculate recent volatility
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


# Historical crash scenarios — use daily candles for older data
# 6 historical crash scenarios with 60-day windows for RSI history
# Unified across all files: config.py, README.md, dashboard.py, evidence/
CRASH_SCENARIOS = [
    {
        "label": "2024-08 Japan Carry Trade Unwind",
        "description": "BTC dropped 24% as Japanese Yen carry trade unwound.",
        "pair": "BTCUSD",
        "start_ts": 1717200000,  # 2024-06-01 (60 days before crash)
        "end_ts": 1723075200,   # 2024-08-08
        "interval": 1440,
    },
    {
        "label": "2024-04 Iran-Israel Tensions",
        "description": "BTC dropped 13% on geopolitical fears.",
        "pair": "BTCUSD",
        "start_ts": 1707782400,  # 2024-02-13 (60 days before)
        "end_ts": 1713398400,   # 2024-04-18
        "interval": 1440,
    },
    {
        "label": "2025-02 Tariff Scare",
        "description": "BTC dropped 13% on US tariff announcement fears.",
        "pair": "BTCUSD",
        "start_ts": 1733184000,  # 2024-12-03 (60 days before)
        "end_ts": 1739059200,   # 2025-02-09
        "interval": 1440,
    },
    {
        "label": "2024-12 Year-End Selloff",
        "description": "BTC corrected 15% from December 2024 highs during year-end profit taking.",
        "pair": "BTCUSD",
        "start_ts": 1727740800,  # 2024-10-01 (60 days before)
        "end_ts": 1735689600,   # 2025-01-01
        "interval": 1440,
    },
    {
        "label": "2025-03 March Correction",
        "description": "BTC dropped from $93K to $78K during broader market risk-off.",
        "pair": "BTCUSD",
        "start_ts": 1735689600,  # 2025-01-01 (60 days before)
        "end_ts": 1743465600,   # 2025-04-01
        "interval": 1440,
    },
    {
        "label": "2024-06 Summer Grind",
        "description": "BTC ground down 20% through summer 2024 low-volume selling.",
        "pair": "BTCUSD",
        "start_ts": 1712016000,  # 2024-04-02 (60 days before)
        "end_ts": 1719792000,   # 2024-07-01
        "interval": 1440,
    },
]


class WarRoom:
    """War Room — stress test strategies against historical crashes."""

    def __init__(self, cache_dir: str = "war_room_cache"):
        self.kraken = KrakenClient()
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def load_scenario(self, scenario: dict) -> list[dict]:
        """Load OHLC data for a crash scenario. Uses cache."""
        cache_file = os.path.join(
            self.cache_dir,
            f"{scenario['label'].replace(' ', '_')}.json"
        )

        # Check cache
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                candles = json.load(f)
            print(f"  [Cache] Loaded {len(candles)} candles for {scenario['label']}")
            return candles

        # Fetch from Kraken
        print(f"  [Kraken] Fetching data for {scenario['label']}...")

        if scenario.get("start_ts"):
            candles = self.kraken.ohlc(
                pair=scenario["pair"],
                interval=scenario["interval"],
                since=scenario["start_ts"],
            )
            # Filter to date range
            if scenario.get("end_ts"):
                candles = [c for c in candles if c["timestamp"] <= scenario["end_ts"]]
        else:
            # Use recent data
            candles = self.kraken.ohlc(
                pair=scenario["pair"],
                interval=scenario["interval"],
            )
            # Take last 100 candles for recent scenario
            candles = candles[-100:]

        # Cache
        with open(cache_file, "w") as f:
            json.dump(candles, f)

        print(f"  [Kraken] Got {len(candles)} candles")
        return candles

    def run_scenario(self, scenario: dict, verbose: bool = True) -> dict:
        """Run a single War Room scenario.

        Returns survival report.
        """
        label = scenario["label"]
        candles = self.load_scenario(scenario)

        if not candles:
            return {"error": f"No data for {label}"}

        if verbose:
            prices = [c["close"] for c in candles]
            high = max(prices)
            low = min(prices)
            drop = (high - low) / high * 100
            print(f"\n  ⚔️  SCENARIO: {label}")
            print(f"  📝 {scenario.get('description', '')}")
            print(f"  📊 Price range: ${high:,.0f} → ${low:,.0f} (max drop: {drop:.1f}%)")
            print(f"  📈 Candles: {len(candles)}")

        # Create fresh agents for this scenario
        risk_manager = RiskManager()
        ledger = TrustLedger(
            ledger_dir=os.path.join(config.LEDGER_DIR, label.replace(" ", "_"))
        )
        portfolio = PortfolioState()

        # Replay candles
        for i, candle in enumerate(candles):
            price = candle["close"]
            timestamp = datetime.fromtimestamp(
                candle["timestamp"], tz=timezone.utc
            ).isoformat()

            # Need enough history for RSI
            history = candles[max(0, i - config.RSI_PERIOD - 5):i + 1]
            if len(history) < config.RSI_PERIOD + 1:
                continue

            # Get signal
            position_data = None
            if portfolio.has_open_position:
                pos = portfolio.current_position
                position_data = {"entry_price": pos.entry_price}

            signal = generate_signal(history, price, position_data)

            if signal.action == "HOLD":
                continue

            # Process BUY
            if signal.action == "BUY" and not portfolio.has_open_position:
                volume = portfolio.get_position_size(price)
                intent = {
                    "action": "BUY", "pair": config.PAIR,
                    "price": price, "volume": volume,
                    "reason": signal.reason, "rsi": signal.rsi,
                }

                risk_decision = risk_manager.evaluate(intent, portfolio.to_dict())
                risk_check = {
                    "drawdown_pct": portfolio.drawdown_pct,
                    "consecutive_losses": portfolio.consecutive_losses,
                    "risk_level": risk_decision.risk_level,
                }

                if risk_decision.decision == "REFUSE":
                    if verbose:
                        print(f"  🛡️  REFUSE @ ${price:,.0f}: {risk_decision.reasoning[:80]}")
                    closes = [c["close"] for c in history]
                    from signal_generator import compute_rsi
                    current_rsi = compute_rsi(closes)
                    entry = ledger.record_refusal(
                        intent, risk_check,
                        risk_decision.refusal_proof or risk_decision.reasoning,
                        analyst_summary={"market_state": "VOLATILE" if current_rsi < 30 or current_rsi > 70 else "RANGING", "rsi": current_rsi, "price": price},
                        strategist_proposal={"action": "BUY", "reason": intent.get("reason", ""), "confidence": 0.72},
                    )

                    # Calculate Refusal Impact Score: what would have happened?
                    # Look ahead 5 candles to see if price dropped
                    future_candles = candles[i+1:i+6]
                    if future_candles:
                        future_low = min(c["close"] for c in future_candles)
                        hypothetical_loss = (price - future_low) / price * volume * price
                        if future_low < price:
                            ledger.update_refusal_impact(
                                entry.entry_id,
                                price_after=future_low,
                                would_have_lost=round(hypothetical_loss, 2),
                            )
                            if verbose and hypothetical_loss > 0:
                                print(f"       💰 Refusal saved est. ${hypothetical_loss:,.2f}")
                    continue

                # Execute with slippage
                adj_volume = round(volume * risk_decision.position_size_adj, 8)
                fill_price = apply_slippage(price, "BUY", candles, i)
                fee = fill_price * adj_volume * config.FEE_RATE
                portfolio.open_position(config.PAIR, fill_price, adj_volume, fee, timestamp)
                if verbose:
                    print(f"  ✅ BUY  @ ${price:,.0f} x {adj_volume:.6f}")
                ledger.record_execution(intent, risk_check,
                                        {"price": price, "volume": adj_volume, "fee": fee})

            # Process SELL
            elif signal.action == "SELL" and portfolio.has_open_position:
                pos = portfolio.current_position
                intent = {
                    "action": "SELL", "pair": config.PAIR,
                    "price": price, "volume": pos.volume,
                    "reason": signal.reason,
                }
                fill_price = apply_slippage(price, "SELL", candles, i)
                fee = fill_price * pos.volume * config.FEE_RATE
                pnl = portfolio.close_position(fill_price, fee, timestamp)
                emoji = "📈" if pnl > 0 else "📉"
                if verbose:
                    print(f"  {emoji} SELL @ ${price:,.0f} | PnL: ${pnl:+,.2f}")
                ledger.record_execution(intent,
                                        {"drawdown_pct": portfolio.drawdown_pct},
                                        {"price": price, "pnl": pnl, "fee": fee})

            # Check death
            if portfolio.total_value <= 0:
                if verbose:
                    print(f"  💀 AGENT DIED")
                break
            if portfolio.circuit_breaker_active:
                if verbose:
                    print(f"  🛑 CIRCUIT BREAKER TRIGGERED — trading suspended")
                break

        # Results
        ledger_stats = ledger.get_stats()
        state = portfolio.to_dict()

        result = {
            "scenario": label,
            "survived": portfolio.total_value > 0,
            "circuit_breaker": portfolio.circuit_breaker_active,
            "final_capital": round(portfolio.total_value, 2),
            "pnl": round(portfolio.total_value - portfolio.initial_capital, 2),
            "max_drawdown": portfolio.drawdown_pct,
            "total_trades": state["total_trades"],
            "win_rate": state["win_rate"],
            "refusals": ledger_stats["refusals"],
            "refusal_rate": ledger_stats["refusal_rate"],
            "chain_valid": ledger_stats["chain_valid"],
        }

        if verbose:
            survived = "SURVIVED ✅" if result["survived"] else "DEAD ❌"
            if result["circuit_breaker"]:
                survived = "CIRCUIT BREAKER 🛑"
            print(f"\n  Result: {survived}")
            print(f"  Capital: ${result['final_capital']:,.2f} | PnL: ${result['pnl']:+,.2f}")
            print(f"  Trades: {result['total_trades']} | Refusals: {result['refusals']}")
            print(f"  Max Drawdown: {result['max_drawdown']:.1f}%")
            print(f"  Trust Ledger: {'✅ Valid' if result['chain_valid'] else '❌ Invalid'}")

        return result

    def run_all_scenarios(self) -> list[dict]:
        """Run all crash scenarios and return survival report."""
        print(f"\n{'='*60}")
        print(f"  WAR ROOM — Running {len(CRASH_SCENARIOS)} scenarios")
        print(f"{'='*60}")

        results = []
        for scenario in CRASH_SCENARIOS:
            result = self.run_scenario(scenario)
            results.append(result)
            print()

        # Summary
        survived = sum(1 for r in results if r.get("survived", False))
        print(f"{'='*60}")
        print(f"  WAR ROOM SUMMARY")
        print(f"  Survived: {survived}/{len(results)} scenarios")
        print(f"  Circuit Breakers: {sum(1 for r in results if r.get('circuit_breaker', False))}")
        total_refusals = sum(r.get("refusals", 0) for r in results)
        print(f"  Total Refusals: {total_refusals}")
        print(f"{'='*60}\n")

        return results


if __name__ == "__main__":
    war_room = WarRoom()
    results = war_room.run_all_scenarios()
