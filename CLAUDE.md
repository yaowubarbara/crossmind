# CrossMind Development Rules

## HARNESS ENGINEERING — 3 Agent Workflow
Every feature MUST go through this cycle:
1. **Builder** (main agent): writes the code
2. **Reviewer** (background agent): checks for bugs, edge cases, security
3. **Advisor** (background agent): suggests improvements for winning

Builder MUST NOT proceed to next feature until Reviewer reports back.

## MANDATORY: After completing EACH feature
1. Update feature_list.json (passes: true)
2. Update PROGRESS.md with what was done
3. **Record a demo video with Playwright** (every feature = 1 demo)
4. Send demo to Barbara's desktop via scp
5. **Wait for Reviewer agent results before next feature**
6. Fix any bugs Reviewer found
7. Apply Advisor suggestions if time permits

## NEVER stop working until Barbara says stop
- Do not ask "want to continue?"
- Do not suggest taking a break
- Keep building features until all 25 are done

## Demo Recording Command
```python
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        record_video_dir='demo_videos',
        record_video_size={'width': 1280, 'height': 720},
    )
    page = ctx.new_page()
    page.goto('file:///path/to/demo.html', wait_until='domcontentloaded')
    time.sleep(5)
    page.screenshot(path='/tmp/demo_screenshot.png')
    ctx.close()
    browser.close()
```

## Project Structure
- config.py: All parameters
- kraken_client.py: Kraken CLI wrapper
- signal_generator.py: RSI signals
- portfolio.py: Capital/position tracking
- risk_manager.py: Claude-powered risk agent
- adversary.py: Claude-powered red team agent
- trust_ledger.py: SHA-256 hash chain
- orchestrator.py: Main trading loop
- war_room.py: Historical crash replay
- gatekeeper.py: Survival scoring
- dashboard.py: Streamlit dashboard
- run_full_pipeline.py: End-to-end entry point

## Trading Parameters (from quant expert)
- RSI(14), 4H candles, entry <35, exit >60
- Stop loss 2%, take profit 4%
- Max drawdown 5%, max consecutive losses 3
- Position size 5%, no weekend, no US market open

## Testing
- Run: python3 orchestrator.py --mode live --iterations 3
- Run: python3 war_room.py
- Run: python3 gatekeeper.py
- Run: python3 run_full_pipeline.py --iterations 3

## NO Claude branding
- No purple (#7b2ff7) colors
- Use green (#10b981) + gold (#f59e0b)
- Say "LLM Agent" not "Claude AI"
- Say "transparent" not "trustless"
