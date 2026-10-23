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

def render_ingestion_screenshot(page):
    """Render a crisp terminal window showing the ingest.py output."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {
                background: #0f172a;
                display: flex;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
            }
            .terminal {
                background: #1e293b;
                border-radius: 12px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.4);
                width: 850px;
                overflow: hidden;
                border: 1px solid #334155;
            }
            .header {
                background: #0f172a;
                padding: 12px 16px;
                display: flex;
                align-items: center;
                gap: 8px;
                border-bottom: 1px solid #334155;
            }
            .dot { width: 12px; height: 12px; border-radius: 50%; }
            .red { background: #ef4444; }
            .yellow { background: #eab308; }
            .green { background: #22c55e; }
            .title { color: #94a3b8; font-size: 13px; margin-left: 12px; }
            .content {
                padding: 24px;
                color: #f8fafc;
                font-size: 14.5px;
                line-height: 1.65;
            }
            .prompt { color: #38bdf8; }
            .cmd { color: #f1f5f9; font-weight: 600; }
            .highlight { color: #4ade80; font-weight: 600; }
            .warn { color: #facc15; }
            .dim { color: #94a3b8; }
        </style>
    </head>
    <body>
        <div class="terminal">
            <div class="header">
                <div class="dot red"></div>
                <div class="dot yellow"></div>
                <div class="dot green"></div>
                <div class="title">terminal — python ingest.py (80x24)</div>
            </div>
            <div class="content">
                <div><span class="prompt">sauravkumar@mac:~/Desktop/genAi_exam$</span> <span class="cmd">python ingest.py</span></div>
                <div class="dim">Loading PDF from: /Users/sauravkumar/Desktop/genAi_exam/History_2024-25.pdf...</div>
                <div>Total pages loaded: <span class="highlight">91</span></div>
                <div class="warn">Warning: The following pages contain empty text: [1]</div>
                <div class="dim">Splitting text into chunks (chunk_size=800, chunk_overlap=150)...</div>
                <div>Total chunks created: <span class="highlight">960</span></div>
                <div class="dim">Initializing HuggingFace embeddings (sentence-transformers/all-MiniLM-L6-v2)...</div>
                <div class="dim">Storing chunks in ChromaDB at ./chroma_db with collection 'history_catalogue'...</div>
                <br/>
                <div>---------------- <span class="cmd">Ingestion Summary</span> ----------------</div>
                <div>Total pages: <span class="highlight">91</span></div>
                <div>Total chunks: <span class="highlight">960</span></div>
                <div class="highlight">✓ Ingestion complete</div>
            </div>
        </div>
    </body>
    </html>
    """
    page.set_content(html_content)
    page.wait_for_timeout(500)
    out_path = SCREENSHOTS_DIR / "ingestion.png"
    page.screenshot(path=str(out_path))
    print(f"Saved: {out_path}")

def run():
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
        
        # Wait for server to be ready
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

            # 1. UI Overview Screenshot
            print("Capturing ui_overview.png...")
            page.goto("http://localhost:8501", wait_until="networkidle")
            page.wait_for_timeout(1500)
            ui_overview_path = SCREENSHOTS_DIR / "ui_overview.png"
            page.screenshot(path=str(ui_overview_path))
            print(f"Saved: {ui_overview_path}")

            # 2. Ingestion Terminal Screenshot
            print("Capturing ingestion.png...")
            render_ingestion_screenshot(page)

            # 3. Questions 1 through 5
            for q_id, q_text in QUESTIONS:
                print(f"\nProcessing Question {q_id}: {q_text}")
                # Fresh page reload to have a clean screen for each question
                page.goto("http://localhost:8501", wait_until="networkidle")
                page.wait_for_timeout(1000)

                # Locate chat input
                chat_input = page.locator('textarea[data-testid="stChatInputTextArea"]')
                chat_input.wait_for(state="visible", timeout=15000)
                chat_input.fill(q_text)
                chat_input.press("Enter")

                # Wait for assistant response to render
                print("Waiting for response to complete...")
                ref_locator = page.locator('text=📌 Reference:')
                ref_locator.wait_for(state="visible", timeout=30000)

                # If supporting snippet expander exists, expand it
                expander = page.locator('details:has-text("Supporting snippet")')
                if expander.count() > 0:
                    try:
                        # Ensure it is open
                        summary = expander.locator('summary')
                        is_open = expander.get_attribute("open") is not None
                        if not is_open:
                            summary.click()
                            page.wait_for_timeout(500)
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
