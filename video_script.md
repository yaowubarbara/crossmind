# CrossMind — 3-Minute Demo Video Script

## SCREEN SETUP
- Browser: HuggingFace Spaces dashboard (https://huggingface.co/spaces/barbarawu/crossmind-dashboard)
- Second tab: BaseScan ERC-8004 registration TX
- Second tab: GitHub repo

---

## 0:00–0:20 — HOOK (show dashboard hero section)

**Screen**: Dashboard homepage — CROSSMIND title with green glow, hero metrics visible

**Voiceover**:
"Every AI trading bot promises to make you money. 73% of them fail within 6 months. CrossMind is different — it's designed to survive first, profit second. And it can prove exactly when refusing to trade saved capital."

---

## 0:20–0:50 — WAR ROOM (click War Room tab)

**Screen**: Click "WAR ROOM" tab — show survival score 6/6, scenario cards

**Voiceover**:
"Before any strategy touches real capital, it must survive our War Room. We replay 6 real market crashes using Kraken historical data — the Japan Carry Trade Unwind where BTC dropped 24%, the Iran-Israel tensions, the 2025 Tariff Scare."

**Screen**: Scroll through scenario cards, pointing out max drawdown and refusal counts

"CrossMind survived all six. Maximum drawdown: 1.9% during a 24% crash. Four unsafe trades were blocked by the Risk Manager."

---

## 0:50–1:30 — TRUST LEDGER (click Trust Ledger tab)

**Screen**: Click "TRUST LEDGER" tab — show stats row, then scroll through entries

**Voiceover**:
"Every decision — whether to trade or refuse — is recorded in the Trust Ledger. Each entry contains the trade intent, risk check, decision, result, and a detailed refusal proof."

**Screen**: Point at a [REFUSE] entry with amber border

"Here's a refusal: the agent detected a buy signal, but the risk check flagged excessive drawdown. Instead of trading, it recorded exactly why it refused."

**Screen**: Point at a [EXECUTE] entry with green border

"And here's an approved trade — RSI oversold, risk check passed, executed via Kraken CLI."

**Screen**: Click "VERIFY HASH CHAIN INTEGRITY" button

"Every entry is SHA-256 hashed and chained. Click verify — if anyone tampers with the ledger, the chain breaks. This is not a database. It's cryptographic proof."

---

## 1:30–2:10 — ARCHITECTURE (click Architecture tab)

**Screen**: Click "ARCHITECTURE" tab — show agent cards and pipeline

**Voiceover**:
"CrossMind uses four agents. Two are deterministic — the Analyst calculates RSI, the Strategist generates signals. Fast, reliable, no hallucination."

**Screen**: Point at AI-Powered Agents card

"Two are AI-powered — the Risk Manager approves or refuses trades with structured reasoning. The Adversary red-teams the strategy in the War Room, finding weaknesses before real capital is at risk."

**Screen**: Show Decision Pipeline diagram

"The pipeline: market data flows through the Analyst, to the Strategist, to the Risk Manager. Every decision ends in the Trust Ledger."

---

## 2:10–2:40 — ERC-8004 + LIVE STATUS

**Screen**: Switch to BaseScan tab — show the ERC-8004 registration TX

**Voiceover**:
"CrossMind is registered on the ERC-8004 Identity Registry — Agent number 3429 on Base Sepolia. This gives it an on-chain verifiable identity with validation artifacts."

**Screen**: Switch back to dashboard, click "LIVE STATUS" tab

"In live mode, CrossMind connects to Kraken CLI for real-time market data. RSI signals, paper trading execution, Dead Man's Switch protection — all through Kraken's AI-native infrastructure."

---

## 2:40–3:00 — CLOSE

**Screen**: Dashboard hero section with metrics visible

**Voiceover**:
"CrossMind is not a trading bot. It's a capital protection system that happens to trade. War Room stress-tested. Trust Ledger verified. ERC-8004 registered. Built on Kraken CLI."

**Screen**: Fade to black with text:
```
CrossMind
github.com/yaowubarbara/crossmind
Agent #3429 — ERC-8004 Identity Registry
```

---

## RECORDING TIPS
- Use OBS Studio or Windows Game Bar (Win+G) to record
- Resolution: 1920x1080
- Record browser full screen
- Speak slowly and clearly
- Upload to YouTube as unlisted, put link in submission
