"""Kraken CLI wrapper — all Kraken operations go through here."""

import json
import subprocess
from datetime import datetime, timezone
from typing import Optional


class KrakenClient:
    """Thin wrapper around Kraken CLI commands."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._kraken_bin = "kraken"

    def _run(self, args: list[str]) -> dict | list:
        """Execute a kraken CLI command and return parsed JSON."""
        cmd = [self._kraken_bin] + args + ["-o", "json"]
        if self.dry_run:
            print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
            return {"dry_run": True, "command": cmd}
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"Kraken CLI error: {result.stderr.strip()}")
        return json.loads(result.stdout)

    # --- Market Data ---

    def ticker(self, pair: str = "BTC/USD") -> dict:
        """Get current ticker data."""
        data = self._run(["ticker", pair])
        # Parse the nested structure — try both formats
        key = pair
        if key not in data:
            key = pair.replace("/", "")
        if key in data:
            t = data[key]
            return {
                "ask": float(t["a"][0]),
                "bid": float(t["b"][0]),
                "last": float(t["c"][0]),
                "high_24h": float(t["h"][0]),
                "low_24h": float(t["l"][0]),
                "open": float(t["o"]),
                "volume_24h": float(t["v"][1]),
                "vwap_24h": float(t["p"][1]),
                "trades_24h": int(t["t"][1]),
            }
        return data

    def ohlc(self, pair: str = "BTCUSD", interval: int = 240, since: Optional[int] = None) -> list[dict]:
        """Get OHLC candle data. interval in minutes."""
        args = ["ohlc", pair, "--interval", str(interval)]
        if since:
            args += ["--since", str(since)]
        data = self._run(args)
        # Parse into list of candles
        candles = []
        if isinstance(data, dict):
            for key, values in data.items():
                if key == "last":
                    continue
                if isinstance(values, list):
                    for v in values:
                        if isinstance(v, list) and len(v) >= 7:
                            candles.append({
                                "timestamp": int(v[0]),
                                "open": float(v[1]),
                                "high": float(v[2]),
                                "low": float(v[3]),
                                "close": float(v[4]),
                                "vwap": float(v[5]),
                                "volume": float(v[6]),
                                "count": int(v[7]) if len(v) > 7 else 0,
                            })
        return sorted(candles, key=lambda c: c["timestamp"])

    def orderbook(self, pair: str = "BTC/USD", count: int = 10) -> dict:
        """Get order book."""
        return self._run(["orderbook", pair, "--count", str(count)])

    def recent_trades(self, pair: str = "BTC/USD") -> dict:
        """Get recent trades."""
        return self._run(["trades", pair])

    # --- Paper Trading ---

    def paper_init(self, balance: float = 10000.0) -> dict:
        """Initialize paper trading."""
        return self._run(["paper", "init"])

    def paper_balance(self) -> dict:
        """Get paper trading balance."""
        return self._run(["paper", "balance"])

    def paper_buy(self, pair: str = "BTC/USD", volume: float = 0.01,
                  order_type: str = "market") -> dict:
        """Place a paper buy order."""
        args = ["paper", "buy", pair, str(volume), "--type", order_type]
        return self._run(args)

    def paper_sell(self, pair: str = "BTC/USD", volume: float = 0.01,
                   order_type: str = "market") -> dict:
        """Place a paper sell order."""
        args = ["paper", "sell", pair, str(volume), "--type", order_type]
        return self._run(args)

    def paper_status(self) -> dict:
        """Get paper trading status with P&L."""
        return self._run(["paper", "status"])

    def paper_history(self) -> dict:
        """Get paper trade history."""
        return self._run(["paper", "history"])

    def paper_reset(self, balance: float = 10000.0) -> dict:
        """Reset paper trading account."""
        return self._run(["paper", "reset"])

    # --- Utilities ---

    def server_time(self) -> dict:
        """Get Kraken server time."""
        return self._run(["server-time"])

    def status(self) -> dict:
        """Get system status."""
        return self._run(["status"])


if __name__ == "__main__":
    client = KrakenClient()
    print("=== Ticker ===")
    print(json.dumps(client.ticker(), indent=2))
    print("\n=== Paper Balance ===")
    print(json.dumps(client.paper_balance(), indent=2))
