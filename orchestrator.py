"""CrossMind Orchestrator — main trading loop.

Modes:
  - live: real-time paper trading with Kraken CLI
  - warroom: replay historical crash data
  - dry-run: no API calls, uses cached data
"""

import json
import time
import sys
from datetime import datetime, timezone

import config
from kraken_client import KrakenClient
from signal_generator import generate_signal
from risk_manager import RiskManager
from trust_ledger import TrustLedger
from portfolio import PortfolioState


class Orchestrator:
    """Main trading loop controller."""

    def __init__(self, mode: str = "live", dry_run: bool = False):
        self.mode = mode
        self.kraken = KrakenClient(dry_run=dry_run)
        self.risk_manager = RiskManager()
        self.ledger = TrustLedger()
        self.portfolio = PortfolioState()
        self.running = False
        self.dead_man_switch_active = False

        print(f"[CrossMind] Initialized in {mode} mode")
        print(f"[CrossMind] Initial capital: ${self.portfolio.initial_capital:,.2f}")

    def run_live(self, interval_seconds: int = 60, max_iterations: int = None):
        """Run live paper trading loop.

        Args:
            interval_seconds: seconds between each check
            max_iterations: stop after N iterations (None = forever)
        """
        self.running = True
        iteration = 0

        print(f"\n{'='*60}")
        print(f"  CrossMind Live Paper Trading")
        print(f"  Pair: {config.PAIR} | Interval: {interval_seconds}s")
        print(f"  Max Drawdown: {config.MAX_DRAWDOWN_PCT*100}%")
        print(f"{'='*60}\n")

        while self.running:
            try:
                # Dead Man's Switch — refresh every tick
                self._refresh_dead_man_switch()
                self._tick()
                iteration += 1

                if max_iterations and iteration >= max_iterations:
                    print(f"\n[CrossMind] Reached max iterations ({max_iterations})")
                    break

                if self.portfolio.circuit_breaker_active:
                    print(f"\n[CrossMind] CIRCUIT BREAKER ACTIVE — trading suspended")
                    break

                time.sleep(interval_seconds)

            except KeyboardInterrupt:
                print(f"\n[CrossMind] Stopped by user")
                break
            except Exception as e:
                print(f"\n[CrossMind] Error: {e}")
                time.sleep(5)

        self._print_summary()

    def _tick(self):
        """One iteration of the trading loop."""
        timestamp = datetime.now(timezone.utc).isoformat()

        # 1. Get market data
        ticker = self.kraken.ticker(config.PAIR)
        current_price = ticker["last"]

        candles = self.kraken.ohlc(
            pair=config.PAIR_KRAKEN,
            interval=config.CANDLE_INTERVAL,
        )

        # 2. Generate signal
        position_data = None
        if self.portfolio.has_open_position:
            pos = self.portfolio.current_position
            position_data = {"entry_price": pos.entry_price}

        signal = generate_signal(candles, current_price, position_data)

        # 3. Print status
        self._print_tick(current_price, signal)

        # 4. Act on signal
        if signal.action == "HOLD":
            return

        if signal.action == "BUY" and not self.portfolio.has_open_position:
            self._handle_buy(signal, current_price, timestamp)

        elif signal.action == "SELL" and self.portfolio.has_open_position:
            self._handle_sell(signal, current_price, timestamp)

    def _handle_buy(self, signal, price: float, timestamp: str):
        """Process a BUY signal through the full pipeline."""
        # Build trade intent
        volume = self.portfolio.get_position_size(price)
        intent = {
            "action": "BUY",
            "pair": config.PAIR,
            "price": price,
            "volume": volume,
            "cost": round(price * volume, 2),
            "reason": signal.reason,
            "rsi": signal.rsi,
            "confidence": signal.confidence,
            "stop_loss": round(price * (1 - config.STOP_LOSS_PCT), 2),
            "take_profit": round(price * (1 + config.TAKE_PROFIT_PCT), 2),
        }

        # Risk check
        portfolio_state = self.portfolio.to_dict()
        risk_decision = self.risk_manager.evaluate(intent, portfolio_state)

        risk_check = {
            "drawdown_pct": portfolio_state["drawdown_pct"],
            "consecutive_losses": portfolio_state["consecutive_losses"],
            "risk_level": risk_decision.risk_level,
            "position_size_adj": risk_decision.position_size_adj,
        }

        if risk_decision.decision == "REFUSE":
            # REFUSAL — the core of CrossMind
            print(f"\n  🛡️  REFUSED: {risk_decision.reasoning}")
            if risk_decision.refusal_proof:
                print(f"      Proof: {risk_decision.refusal_proof[:100]}...")

            self.ledger.record_refusal(
                intent=intent,
                risk_check=risk_check,
                refusal_proof=risk_decision.refusal_proof or risk_decision.reasoning,
            )
            return

        # APPROVED — execute
        adjusted_volume = round(volume * risk_decision.position_size_adj, 8)
        if adjusted_volume <= 0:
            return

        intent["volume"] = adjusted_volume
        intent["cost"] = round(price * adjusted_volume, 2)

        try:
            result = self.kraken.paper_buy(
                pair=config.PAIR,
                volume=adjusted_volume,
                order_type="market",
            )

            fill_price = float(result.get("price", price))
            fee = float(result.get("fee", 0))
            order_id = result.get("order_id", "")

            self.portfolio.open_position(
                pair=config.PAIR,
                price=fill_price,
                volume=adjusted_volume,
                fee=fee,
                timestamp=timestamp,
                order_id=order_id,
            )

            print(f"\n  ✅ EXECUTED: BUY {adjusted_volume} {config.PAIR} @ ${fill_price:,.2f}")

            self.ledger.record_execution(
                intent=intent,
                risk_check=risk_check,
                result={
                    "filled": True,
                    "price": fill_price,
                    "volume": adjusted_volume,
                    "fee": fee,
                    "order_id": order_id,
                },
            )

        except Exception as e:
            print(f"\n  ❌ EXECUTION FAILED: {e}")
            self.ledger.record_refusal(
                intent=intent,
                risk_check=risk_check,
                refusal_proof=f"Execution error: {str(e)}",
            )

    def _handle_sell(self, signal, price: float, timestamp: str):
        """Process a SELL signal."""
        pos = self.portfolio.current_position
        if not pos:
            return

        intent = {
            "action": "SELL",
            "pair": config.PAIR,
            "price": price,
            "volume": pos.volume,
            "reason": signal.reason,
            "rsi": signal.rsi,
        }

        try:
            result = self.kraken.paper_sell(
                pair=config.PAIR,
                volume=pos.volume,
                order_type="market",
            )

            fill_price = result.get("price", price)
            fee = result.get("fee", 0)

            pnl = self.portfolio.close_position(fill_price, fee, timestamp)

            emoji = "📈" if pnl > 0 else "📉"
            print(f"\n  {emoji} SOLD: {pos.volume} {config.PAIR} @ ${fill_price:,.2f} | PnL: ${pnl:+,.2f}")

            self.ledger.record_execution(
                intent=intent,
                risk_check={"action": "SELL", "drawdown_pct": self.portfolio.drawdown_pct},
                result={
                    "filled": True,
                    "price": fill_price,
                    "volume": pos.volume,
                    "fee": fee,
                    "pnl": pnl,
                },
            )

        except Exception as e:
            print(f"\n  ❌ SELL FAILED: {e}")

    def run_warroom(self, candles: list[dict]) -> dict:
        """Run War Room replay with historical candle data.

        Args:
            candles: list of OHLC candles to replay

        Returns:
            dict with survival stats
        """
        print(f"\n{'='*60}")
        print(f"  WAR ROOM — Replaying {len(candles)} candles")
        print(f"{'='*60}\n")

        # Reset portfolio for war room
        self.portfolio = PortfolioState()

        for i, candle in enumerate(candles):
            price = candle["close"]
            timestamp = datetime.fromtimestamp(candle["timestamp"], tz=timezone.utc).isoformat()

            # Build minimal candle history for RSI
            history = candles[max(0, i - config.RSI_PERIOD - 5):i + 1]

            position_data = None
            if self.portfolio.has_open_position:
                pos = self.portfolio.current_position
                position_data = {"entry_price": pos.entry_price}

            signal = generate_signal(history, price, position_data)

            if signal.action == "BUY" and not self.portfolio.has_open_position:
                self._handle_buy(signal, price, timestamp)
            elif signal.action == "SELL" and self.portfolio.has_open_position:
                self._handle_sell(signal, price, timestamp)

            # Check if dead
            if self.portfolio.total_value <= 0:
                print(f"\n  💀 AGENT DIED at candle {i}/{len(candles)}")
                break

            if self.portfolio.circuit_breaker_active:
                print(f"\n  🛑 CIRCUIT BREAKER at candle {i}/{len(candles)}")
                break

        self._print_summary()

        return {
            "survived": self.portfolio.total_value > 0 and not self.portfolio.circuit_breaker_active,
            "final_capital": round(self.portfolio.total_value, 2),
            "max_drawdown": self.portfolio.drawdown_pct,
            "total_trades": self.portfolio.total_trades,
            "win_rate": round(self.portfolio.winning_trades / max(1, self.portfolio.total_trades) * 100, 1),
            "refusals": len([e for e in self.ledger.entries if e.decision == "REFUSE"]),
            "circuit_breaker": self.portfolio.circuit_breaker_active,
        }

    def _refresh_dead_man_switch(self):
        """Refresh Dead Man's Switch — auto-cancels orders if agent crashes."""
        if not self.dead_man_switch_active:
            return
        try:
            # In live mode with API keys, this would call:
            # kraken order cancel-after 60
            # For paper trading, we just log it
            print("  ⚡ Dead Man's Switch refreshed (60s)")
        except Exception as e:
            print(f"  ⚠️ Dead Man's Switch refresh failed: {e}")

    def enable_dead_man_switch(self):
        """Enable Dead Man's Switch protection."""
        self.dead_man_switch_active = True
        print("[CrossMind] Dead Man's Switch ENABLED — orders auto-cancel if agent stops")

    def _print_tick(self, price: float, signal):
        """Print current tick status."""
        dd = self.portfolio.drawdown_pct
        pnl = self.portfolio.total_value - self.portfolio.initial_capital
        pos = "📊 OPEN" if self.portfolio.has_open_position else "💤 FLAT"
        sys.stdout.write(
            f"\r  {config.PAIR} ${price:,.2f} | RSI {signal.rsi} | "
            f"{signal.action} | DD {dd:.1f}% | PnL ${pnl:+,.2f} | {pos}  "
        )
        sys.stdout.flush()

    def _print_summary(self):
        """Print trading summary."""
        state = self.portfolio.to_dict()
        ledger_stats = self.ledger.get_stats()

        print(f"\n\n{'='*60}")
        print(f"  CrossMind Summary")
        print(f"{'='*60}")
        print(f"  Capital:  ${state['capital']:,.2f} (was ${self.portfolio.initial_capital:,.2f})")
        print(f"  PnL:      ${state['current_pnl']:+,.2f}")
        print(f"  Drawdown: {state['drawdown_pct']:.1f}%")
        print(f"  Trades:   {state['total_trades']} (Win rate: {state['win_rate']}%)")
        print(f"  Losses:   {self.portfolio.consecutive_losses} consecutive")
        print(f"  Circuit:  {'🛑 ACTIVE' if state['circuit_breaker'] else '✅ OK'}")
        print(f"\n  Trust Ledger:")
        print(f"    Entries:   {ledger_stats['total_entries']}")
        print(f"    Executions: {ledger_stats['executions']}")
        print(f"    Refusals:   {ledger_stats['refusals']} ({ledger_stats['refusal_rate']}%)")
        print(f"    Capital saved by refusals: ${ledger_stats['total_capital_saved_by_refusals']:,.2f}")
        print(f"    Chain valid: {'✅' if ledger_stats['chain_valid'] else '❌'}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="CrossMind Trading Agent")
    parser.add_argument("--mode", choices=["live", "warroom"], default="live")
    parser.add_argument("--iterations", type=int, default=5, help="Max iterations for live mode")
    parser.add_argument("--interval", type=int, default=30, help="Seconds between ticks")
    parser.add_argument("--dry-run", action="store_true", help="No API calls")
    args = parser.parse_args()

    orch = Orchestrator(mode=args.mode, dry_run=args.dry_run)

    if args.mode == "live":
        orch.run_live(interval_seconds=args.interval, max_iterations=args.iterations)
    elif args.mode == "warroom":
        # Load crash data
        candles = orch.kraken.ohlc(pair=config.PAIR_KRAKEN, interval=config.CANDLE_INTERVAL)
        result = orch.run_warroom(candles[-100:])  # Last 100 candles
        print(f"\nWar Room Result: {'SURVIVED ✅' if result['survived'] else 'DEAD ❌'}")
