"""Generate voiceover for CrossMind demo video using Edge TTS."""

import asyncio
import edge_tts
import os

VOICE = "en-US-GuyNeural"  # Professional male voice
OUTPUT_DIR = "demo_videos/audio"

# Narration segments timed to video sections
# Video: ~162 seconds total, starts at 0s (8s of load trimmed later)
SEGMENTS = [
    {
        "file": "01_hero.mp3",
        "text": (
            "Every AI trading bot promises to make you money. "
            "73 percent of them fail within six months. "
            "CrossMind is different. It's designed to survive first, profit second. "
            "And it proves exactly when refusing to trade saved capital."
        ),
    },
    {
        "file": "02_live.mp3",
        "text": (
            "In live mode, CrossMind connects to Kraken CLI for real-time market data. "
            "BTC price, RSI indicators, paper trading balance, and the current signal. "
            "All processed through Kraken's AI-native infrastructure."
        ),
    },
    {
        "file": "03_ledger.mp3",
        "text": (
            "The Trust Ledger records every decision. "
            "Each entry contains the trade intent, risk check, decision, and result. "
            "32 decisions recorded. 4 threats blocked. 12 percent refusal rate. "
            "Every entry is SHA-256 hashed and chained to the previous one. "
            "Click verify. If anyone tampers with the ledger, the chain breaks. "
            "This is not a database. It's cryptographic proof."
        ),
    },
    {
        "file": "04_entries.mp3",
        "text": (
            "Here you can see individual decisions. "
            "Green entries are executed trades with their P and L. "
            "The amber entry at the bottom is a refusal. "
            "Trading paused after 3 consecutive losses. "
            "The agent explains why it refused, creating a verifiable refusal proof."
        ),
    },
    {
        "file": "05_warroom.mp3",
        "text": (
            "Before any strategy touches real capital, it must survive the War Room. "
            "We replay 6 real market crashes using Kraken historical data. "
            "The Japan Carry Trade Unwind. BTC dropped 24 percent. "
            "Iran-Israel Tensions. The Tariff Scare. Year-End Selloff. "
            "CrossMind survived all six. "
            "Maximum drawdown: 1.9 percent during a 24 percent crash. "
            "4 unsafe trades were blocked by the Risk Manager."
        ),
    },
    {
        "file": "06_arch.mp3",
        "text": (
            "CrossMind uses 4 agents. Two are deterministic: "
            "the Analyst calculates RSI, the Strategist generates signals. "
            "Fast, reliable, no hallucination. "
            "Two are AI-powered: the Risk Manager approves or refuses trades, "
            "and the Adversary red-teams the strategy in the War Room."
        ),
    },
    {
        "file": "07_pipeline.mp3",
        "text": (
            "The decision pipeline: market data flows through the Analyst, "
            "to the Strategist, to the Risk Manager. "
            "Every decision ends in the Trust Ledger. "
            "Strict risk parameters: 5 percent max drawdown triggers a circuit breaker. "
            "3 consecutive losses pause trading. Position size capped at 10 percent."
        ),
    },
    {
        "file": "08_close.mp3",
        "text": (
            "CrossMind is not a trading bot. "
            "It's a capital protection system that happens to trade. "
            "War Room stress-tested. Trust Ledger verified. "
            "ERC-8004 registered. Agent number 3429. "
            "Built on Kraken CLI."
        ),
    },
]


async def generate_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for seg in SEGMENTS:
        out = os.path.join(OUTPUT_DIR, seg["file"])
        print(f"Generating {seg['file']}...")
        comm = edge_tts.Communicate(seg["text"], VOICE, rate="-5%")
        await comm.save(out)
        print(f"  Saved: {out}")

    print("\nAll segments generated!")
    print(f"Files in {OUTPUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(generate_all())
