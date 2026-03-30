"""Signal Generator — deterministic RSI mean reversion signals."""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
import config


@dataclass
class Signal:
    """A trading signal."""
    action: str          # "BUY", "SELL", "HOLD"
    pair: str
    price: float
    rsi: float
    reason: str
    timestamp: str
    confidence: float    # 0.0 - 1.0


def compute_rsi(closes: list[float], period: int = 14) -> float:
    """Compute RSI from a list of closing prices."""
    if len(closes) < period + 1:
        return 50.0  # neutral if not enough data

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent_deltas = deltas[-(period):]

    gains = [d for d in recent_deltas if d > 0]
    losses = [-d for d in recent_deltas if d < 0]

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0.0001  # avoid div by zero

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def is_weekend() -> bool:
    """Check if current time is weekend (Sat/Sun)."""
    now = datetime.now(timezone.utc)
    return now.weekday() >= 5  # 5=Saturday, 6=Sunday


def is_us_market_open() -> bool:
    """Check if current time is during US market open (13:30-15:00 UTC)."""
    now = datetime.now(timezone.utc)
    hour_decimal = now.hour + now.minute / 60
    return config.US_OPEN_START_UTC <= hour_decimal <= config.US_OPEN_END_UTC


def generate_signal(candles: list[dict], current_price: float,
                    position: Optional[dict] = None) -> Signal:
    """Generate a trading signal from candle data.

    Args:
        candles: list of OHLC candles (need at least RSI_PERIOD + 1)
        current_price: current market price
        position: current open position (if any)

    Returns:
        Signal with action BUY/SELL/HOLD
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    closes = [c["close"] for c in candles]
    rsi = compute_rsi(closes, config.RSI_PERIOD)

    # Time filters
    if config.NO_WEEKEND_TRADING and is_weekend():
        return Signal(
            action="HOLD",
            pair=config.PAIR,
            price=current_price,
            rsi=rsi,
            reason=f"Weekend — no trading. RSI={rsi}",
            timestamp=timestamp,
            confidence=0.0,
        )

    if config.NO_US_OPEN_TRADING and is_us_market_open():
        return Signal(
            action="HOLD",
            pair=config.PAIR,
            price=current_price,
            rsi=rsi,
            reason=f"US market open hours — high volatility, no new entries. RSI={rsi}",
            timestamp=timestamp,
            confidence=0.0,
        )

    # Check if we have an open position → check exit signals
    if position:
        entry_price = position["entry_price"]
        pnl_pct = (current_price - entry_price) / entry_price

        if pnl_pct <= -config.STOP_LOSS_PCT:
            return Signal(
                action="SELL",
                pair=config.PAIR,
                price=current_price,
                rsi=rsi,
                reason=f"Stop loss triggered. Entry={entry_price:.2f}, "
                       f"Current={current_price:.2f}, PnL={pnl_pct*100:.2f}%",
                timestamp=timestamp,
                confidence=0.95,
            )

        if pnl_pct >= config.TAKE_PROFIT_PCT:
            return Signal(
                action="SELL",
                pair=config.PAIR,
                price=current_price,
                rsi=rsi,
                reason=f"Take profit reached. Entry={entry_price:.2f}, "
                       f"Current={current_price:.2f}, PnL={pnl_pct*100:.2f}%",
                timestamp=timestamp,
                confidence=0.90,
            )

        if rsi > config.RSI_SELL_THRESHOLD:
            return Signal(
                action="SELL",
                pair=config.PAIR,
                price=current_price,
                rsi=rsi,
                reason=f"RSI overbought exit. RSI={rsi} > {config.RSI_SELL_THRESHOLD}",
                timestamp=timestamp,
                confidence=0.75,
            )

        return Signal(
            action="HOLD",
            pair=config.PAIR,
            price=current_price,
            rsi=rsi,
            reason=f"Position open, no exit signal. RSI={rsi}, PnL={pnl_pct*100:.2f}%",
            timestamp=timestamp,
            confidence=0.0,
        )

    # No position → check entry signals
    if rsi < config.RSI_BUY_THRESHOLD:
        confidence = min(1.0, (config.RSI_BUY_THRESHOLD - rsi) / 10)  # more oversold = higher confidence
        return Signal(
            action="BUY",
            pair=config.PAIR,
            price=current_price,
            rsi=rsi,
            reason=f"RSI oversold. RSI={rsi} < {config.RSI_BUY_THRESHOLD}. "
                   f"Mean reversion entry.",
            timestamp=timestamp,
            confidence=round(confidence, 2),
        )

    return Signal(
        action="HOLD",
        pair=config.PAIR,
        price=current_price,
        rsi=rsi,
        reason=f"No signal. RSI={rsi} (neutral zone {config.RSI_BUY_THRESHOLD}-{config.RSI_SELL_THRESHOLD})",
        timestamp=timestamp,
        confidence=0.0,
    )
