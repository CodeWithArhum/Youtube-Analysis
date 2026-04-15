"""
Full Pipeline Runner
Runs the complete YouTube analysis pipeline:
1. Scrape YouTube data
2. Analyze the data
3. Build branded PDF report
4. Push analysis to Google Sheets
5. Send report via Gmail

Usage: python tools/run_pipeline.py
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def run_step(name: str, script: str):
    """Run a pipeline step and handle errors."""
    print(f"\n{'='*50}")
    print(f"STEP: {name}")
    print(f"{'='*50}")

    result = subprocess.run(
        [sys.executable, str(TOOLS / script)],
        cwd=str(ROOT),
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"\nERROR: {name} failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    print(f"DONE: {name}")


def main():
    print("YouTube AI Analysis — Full Pipeline")
    print("=" * 50)

    run_step("Scrape YouTube Data", "youtube_scraper.py")
    run_step("Analyze Data", "analyze_data.py")
    run_step("Build PDF Report", "build_pdf.py")
    run_step("Push to Google Sheets", "push_to_sheets.py")
    run_step("Send Report via Gmail", "send_email.py")

    print(f"\n{'='*50}")
    print("PIPELINE COMPLETE — Report sent!")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
