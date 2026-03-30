"""Record Day 1 demo using Playwright."""
import asyncio
from playwright.async_api import async_playwright


async def record_demo():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir="./demo_videos",
            record_video_size={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        # Open the demo HTML
        await page.goto("file:///home/dev/fenxicai/cybersec/kraken-hackathon/crossmind/demo_day1.html")

        # Wait for animations to complete
        await asyncio.sleep(5)

        # Take screenshot too
        await page.screenshot(path="demo_day1_screenshot.png", full_page=True)
        print("Screenshot saved: demo_day1_screenshot.png")

        # Wait a bit more for video
        await asyncio.sleep(3)

        await context.close()
        await browser.close()
        print("Video saved in ./demo_videos/")


if __name__ == "__main__":
    asyncio.run(record_demo())
