"""Portfolio State Tracker — tracks capital, positions, drawdown, losses."""

from dataclasses import dataclass, field
from typing import Optional
import config


@dataclass
class Position:
    """An open trading position."""
    pair: str
    side: str          # "long"
    entry_price: float
    volume: float
    entry_time: str
    order_id: str = ""


@dataclass
class PortfolioState:
    """Current state of the trading portfolio."""
    initial_capital: float = config.INITIAL_CAPITAL
    cash: float = config.INITIAL_CAPITAL
    positions: list = field(default_factory=list)
    trade_history: list = field(default_factory=list)
    consecutive_losses: int = 0
    peak_capital: float = config.INITIAL_CAPITAL
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    circuit_breaker_active: bool = False

    _current_market_price: float = 0.0

    def update_market_price(self, price: float):
        """Update current market price for real-time P&L calculation."""
        self._current_market_price = price

    @property
    def total_value(self) -> float:
        """Total portfolio value (cash + positions at current market price)."""
        if self._current_market_price > 0 and self.positions:
            position_value = sum(self._current_market_price * p.volume for p in self.positions)
        else:
            position_value = sum(p.entry_price * p.volume for p in self.positions)
        return self.cash + position_value

    @property
    def drawdown_pct(self) -> float:
        """Current drawdown as percentage from peak."""
        if self.peak_capital <= 0:
            return 0.0
        dd = (self.peak_capital - self.total_value) / self.peak_capital * 100
        return round(max(0, dd), 2)

    @property
    def has_open_position(self) -> bool:
        return len(self.positions) > 0

    @property
    def current_position(self) -> Optional[Position]:
        return self.positions[0] if self.positions else None

    def update_peak(self):
        """Update peak capital if current value is higher."""
        if self.total_value > self.peak_capital:
            self.peak_capital = self.total_value

    def open_position(self, pair: str, price: float, volume: float,
                      fee: float, timestamp: str, order_id: str = ""):
        """Record opening a position."""
        cost = price * volume + fee
        self.cash -= cost
        self.positions.append(Position(
            pair=pair,
            side="long",
            entry_price=price,
            volume=volume,
            entry_time=timestamp,
            order_id=order_id,
        ))
        self.total_trades += 1

    def close_position(self, price: float, fee: float, timestamp: str) -> float:
        """Close current position and return PnL."""
        if not self.positions:
            return 0.0

        pos = self.positions.pop(0)
        revenue = price * pos.volume - fee
        self.cash += revenue

        entry_cost = pos.entry_price * pos.volume
        entry_fee = entry_cost * 0.0026  # approximate entry fee
        pnl = revenue - entry_cost - entry_fee

        # Track wins/losses
        if pnl > 0:
            self.winning_trades += 1
            self.consecutive_losses = 0
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1

        # Update peak
        self.update_peak()

        # Check circuit breaker
        if self.drawdown_pct >= config.MAX_DRAWDOWN_PCT * 100:
            self.circuit_breaker_active = True

        # Record trade
        self.trade_history.append({
            "pair": pos.pair,
            "entry_price": pos.entry_price,
            "exit_price": price,
            "volume": pos.volume,
            "pnl": round(pnl, 2),
            "fee": fee,
            "entry_time": pos.entry_time,
            "exit_time": timestamp,
        })

        return round(pnl, 2)

    def get_position_size(self, price: float, adjustment: float = 1.0) -> float:
        """Calculate position size based on risk rules."""
        max_spend = self.cash * config.MAX_POSITION_PCT * adjustment
        volume = max_spend / price
        return round(volume, 8)

    def to_dict(self) -> dict:
        """Export state for Risk Manager evaluation."""
        return {
            "capital": round(self.total_value, 2),
            "cash": round(self.cash, 2),
            "drawdown_pct": self.drawdown_pct,
            "consecutive_losses": self.consecutive_losses,
            "open_positions": len(self.positions),
            "total_trades": self.total_trades,
            "win_rate": round(self.winning_trades / max(1, self.total_trades) * 100, 1),
            "circuit_breaker": self.circuit_breaker_active,
            "current_pnl": round(self.total_value - self.initial_capital, 2),
        }
