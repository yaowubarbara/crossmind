"""CrossMind Configuration"""

# Trading pair
PAIR = "BTC/USD"
PAIR_KRAKEN = "BTCUSD"  # Kraken format

# Strategy parameters (from quant expert)
RSI_PERIOD = 14
RSI_BUY_THRESHOLD = 28      # Enter when RSI < 28
RSI_SELL_THRESHOLD = 65      # Exit when RSI > 65
STOP_LOSS_PCT = 0.03         # 3% stop loss
TAKE_PROFIT_PCT = 0.05       # 5% take profit
CANDLE_INTERVAL = 240        # 4-hour candles (minutes)

# Risk management
MAX_DRAWDOWN_PCT = 0.05      # 5% circuit breaker
MAX_CONSECUTIVE_LOSSES = 3   # Pause after 3 losses
MAX_POSITION_PCT = 0.10      # 10% of capital per trade
INITIAL_CAPITAL = 10000.0

# Time filters
NO_WEEKEND_TRADING = True
NO_US_OPEN_TRADING = True    # Skip 13:30-15:00 UTC
US_OPEN_START_UTC = 13.5     # 13:30
US_OPEN_END_UTC = 15.0       # 15:00

# War Room scenarios (historical crashes)
WAR_ROOM_SCENARIOS = [
    {
        "label": "2024-08-05 Japan Carry Trade Unwind",
        "pair": "BTCUSD",
        "start": "2024-08-05T00:00:00Z",
        "end": "2024-08-06T00:00:00Z",
    },
    {
        "label": "2024-04-13 Iran-Israel Tensions",
        "pair": "BTCUSD",
        "start": "2024-04-13T00:00:00Z",
        "end": "2024-04-14T00:00:00Z",
    },
    {
        "label": "2022-11-09 FTX Collapse",
        "pair": "BTCUSD",
        "start": "2022-11-08T00:00:00Z",
        "end": "2022-11-11T00:00:00Z",
    },
]

# Slippage modeling
SLIPPAGE_NORMAL_BPS = 7       # 7 basis points normal
SLIPPAGE_CRASH_BPS = 200      # 200 basis points during crash
VOLATILITY_THRESHOLD = 0.03   # 3% = high volatility

# Fee
FEE_RATE = 0.0026             # 0.26% taker fee

# Claude API
CLAUDE_MODEL = "claude-sonnet-4-6"

# Trust Ledger
LEDGER_DIR = "trust_ledger/records"
