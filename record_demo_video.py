"""Record CrossMind dashboard demo video using Playwright."""

import time
from playwright.sync_api import sync_playwright

DASHBOARD_URL = "https://huggingface.co/spaces/barbarawu/crossmind-dashboard"
VIDEO_DIR = "demo_videos"
VIEWPORT = {"width": 1920, "height": 1080}


def record():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport=VIEWPORT,
            record_video_dir=VIDEO_DIR,
            record_video_size=VIEWPORT,
        )
        page = context.new_page()

        print("[REC] Opening dashboard...")
        page.goto(DASHBOARD_URL, wait_until="networkidle", timeout=60000)
        time.sleep(8)  # Wait for Streamlit to fully render

        # Screenshot: Hero section
        print("[REC] Hero section...")
        page.screenshot(path=f"{VIDEO_DIR}/01_hero.png")
        time.sleep(4)

        # Scroll down slightly to show metrics
        page.mouse.wheel(0, 300)
        time.sleep(3)
        page.screenshot(path=f"{VIDEO_DIR}/02_metrics.png")

        # Click LIVE STATUS tab
        print("[REC] Live Status tab...")
        try:
            page.click("text=LIVE STATUS", timeout=5000)
            time.sleep(4)
            page.screenshot(path=f"{VIDEO_DIR}/03_live_status.png")
        except Exception as e:
            print(f"  Could not click LIVE STATUS: {e}")

        # Click TRUST LEDGER tab
        print("[REC] Trust Ledger tab...")
        try:
            page.click("text=TRUST LEDGER", timeout=5000)
            time.sleep(4)
            page.screenshot(path=f"{VIDEO_DIR}/04_trust_ledger.png")

            # Scroll to show entries
            page.mouse.wheel(0, 400)
            time.sleep(3)
            page.screenshot(path=f"{VIDEO_DIR}/05_ledger_entries.png")

            # Scroll more to show more entries
            page.mouse.wheel(0, 400)
            time.sleep(3)
            page.screenshot(path=f"{VIDEO_DIR}/06_ledger_more.png")

            # Scroll back up to click verify button
            page.mouse.wheel(0, -800)
            time.sleep(2)
            try:
                page.click("text=VERIFY HASH CHAIN", timeout=5000)
                time.sleep(3)
                page.screenshot(path=f"{VIDEO_DIR}/07_verify_hash.png")
            except Exception:
                print("  Could not click verify button")

        except Exception as e:
            print(f"  Could not click TRUST LEDGER: {e}")

        # Click WAR ROOM tab
        print("[REC] War Room tab...")
        try:
            page.click("text=WAR ROOM", timeout=5000)
            time.sleep(4)
            page.screenshot(path=f"{VIDEO_DIR}/08_war_room.png")

            # Scroll to see all scenarios
            page.mouse.wheel(0, 400)
            time.sleep(3)
            page.screenshot(path=f"{VIDEO_DIR}/09_war_room_scenarios.png")
        except Exception as e:
            print(f"  Could not click WAR ROOM: {e}")

        # Click ARCHITECTURE tab
        print("[REC] Architecture tab...")
        try:
            page.click("text=ARCHITECTURE", timeout=5000)
            time.sleep(4)
            page.screenshot(path=f"{VIDEO_DIR}/10_architecture.png")

            # Scroll to pipeline and risk params
            page.mouse.wheel(0, 400)
            time.sleep(3)
            page.screenshot(path=f"{VIDEO_DIR}/11_pipeline.png")

            page.mouse.wheel(0, 400)
            time.sleep(3)
            page.screenshot(path=f"{VIDEO_DIR}/12_risk_params.png")
        except Exception as e:
            print(f"  Could not click ARCHITECTURE: {e}")

        # Scroll back to top for final shot
        print("[REC] Final shot...")
        page.evaluate("window.scrollTo(0, 0)")
        time.sleep(2)
        try:
            page.click("text=LIVE STATUS", timeout=5000)
        except Exception:
            pass
        time.sleep(3)
        page.screenshot(path=f"{VIDEO_DIR}/13_final.png")

        # Close context to save video
        print("[REC] Saving video...")
        video_path = page.video.path()
        context.close()
        browser.close()

        print(f"\n[DONE] Video saved to: {video_path}")
        print(f"[DONE] Screenshots saved to: {VIDEO_DIR}/")
        return video_path


if __name__ == "__main__":
    import os
    os.makedirs(VIDEO_DIR, exist_ok=True)
    record()
