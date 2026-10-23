import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
CHATS_FILE = BASE_DIR / "chats.json"

QUESTIONS = [
    (1, "On what date were the prices in this catalogue last updated?"),
    (2, "In which year was the publisher (Orient BlackSwan) incorporated?"),
    (3, "What is the price of a Physics textbook?"),
    (4, "Who is the current Minister of Education?"),
    (5, 'Which is the "best" history book for a beginner?')
]

def is_server_running(url="http://localhost:8501"):
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False

def run():
    # Clear chats.json first so we start with a clean state
    if CHATS_FILE.exists():
        CHATS_FILE.unlink()

    server_process = None
    if not is_server_running():
        print("Starting Streamlit server on port 8501...")
        streamlit_cmd = [
            str(BASE_DIR / "venv" / "bin" / "streamlit"),
            "run",
            str(BASE_DIR / "ui.py"),
            "--server.port", "8501",
            "--server.headless", "true"
        ]
        server_process = subprocess.Popen(streamlit_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for i in range(30):
            if is_server_running():
                print("Streamlit server is ready!")
                break
            time.sleep(1)
        else:
            raise RuntimeError("Streamlit server failed to start within 30 seconds.")
    else:
        print("Streamlit server is already running on port 8501.")

    try:
        with sync_playwright() as p:
            print("Launching Chromium browser (1400x900)...")
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})

            # 1. UI Overview Screenshot (Welcome Screen)
            print("Capturing ui_overview.png...")
            page.goto("http://localhost:8501", wait_until="networkidle")
            page.wait_for_timeout(2000)
            ui_overview_path = SCREENSHOTS_DIR / "ui_overview.png"
            page.screenshot(path=str(ui_overview_path))
            print(f"Saved: {ui_overview_path}")

            # 2. Questions 1 through 5
            for q_id, q_text in QUESTIONS:
                print(f"\nProcessing Question {q_id}: {q_text}")
                
                # Click "+ New chat" button in sidebar to start fresh conversation
                new_chat_btn = page.locator('button[data-testid="stBaseButton-primary"]')
                if new_chat_btn.count() > 0:
                    new_chat_btn.first.click()
                    page.wait_for_timeout(1000)

                # Locate chat input
                chat_input = page.locator('textarea[data-testid="stChatInputTextArea"]')
                chat_input.wait_for(state="visible", timeout=15000)
                chat_input.fill(q_text)
                chat_input.press("Enter")

                # Wait for assistant response to render
                print("Waiting for response to complete...")
                bot_msg = page.locator('.msg-bot')
                bot_msg.wait_for(state="visible", timeout=35000)
                page.wait_for_timeout(1500)

                # Expand supporting snippet if present
                expander = page.locator('details:has-text("Supporting snippet")')
                if expander.count() > 0:
                    try:
                        summary = expander.locator('summary')
                        is_open = expander.get_attribute("open") is not None
                        if not is_open:
                            summary.click()
                            page.wait_for_timeout(600)
                    except Exception as e:
                        print(f"Note expanding snippet: {e}")

                page.wait_for_timeout(1200)

                # Capture screenshot
                q_screenshot_path = SCREENSHOTS_DIR / f"q{q_id}.png"
                page.screenshot(path=str(q_screenshot_path))
                print(f"Saved: {q_screenshot_path}")

            browser.close()
            print("\nAll screenshots generated successfully in screenshots/")

    finally:
        if server_process:
            print("Stopping Streamlit server...")
            server_process.terminate()

if __name__ == "__main__":
    run()
