"""
Google Sheets Pusher — Analysis Summary
Pushes YouTube analysis results to a Google Sheet via OAuth.

Usage: python tools/push_to_sheets.py
Input: .tmp/analysis_results.json
Requires: OAuth client secret JSON + GOOGLE_SHEETS_ID in .env
"""

import glob
import json
import os
import sys
from pathlib import Path

import gspread
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

INPUT_PATH = ROOT / ".tmp" / "analysis_results.json"
TOKEN_PATH = ROOT / "sheets_token.json"
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def find_client_secret():
    """Find the OAuth client secret JSON file in the project root."""
    for pattern in [str(ROOT / "client_secret*.json"), str(ROOT / "credentials.json")]:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def get_sheets_client():
    """Build Google Sheets client with OAuth."""
    client_secret = find_client_secret()
    if not client_secret:
        print("ERROR: No client_secret*.json found in project root.")
        sys.exit(1)

    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing Sheets token...")
            creds.refresh(Request())
        else:
            print("Opening browser for Google Sheets sign-in...")
            print("(Authorize the app to access Google Sheets)")
            flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print("Sheets token saved.")

    return gspread.authorize(creds)


def ensure_worksheet(spreadsheet, title, headers):
    """Get or create a worksheet with headers."""
    try:
        ws = spreadsheet.worksheet(title)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=title, rows=100, cols=len(headers))
    ws.update([headers], "A1")
    ws.format("A1:Z1", {"textFormat": {"bold": True}})
    return ws


def push_summary(spreadsheet, data):
    """Push summary stats to the Summary tab."""
    summary = data["summary"]
    benchmarks = data["engagement_benchmarks"]

    headers = ["Metric", "Value"]
    ws = ensure_worksheet(spreadsheet, "Summary", headers)

    rows = [
        ["Date Range", summary["date_range"]],
        ["Generated At", data.get("generated_at", "")],
        ["Total Videos", summary["total_videos"]],
        ["Unique Channels", summary["unique_channels"]],
        ["Total Views", summary["total_views"]],
        ["Average Views", summary["avg_views"]],
        ["Median Views", summary["median_views"]],
        ["Max Views", summary["max_views"]],
        ["Median Like Ratio", f"{benchmarks.get('median_like_ratio', 0):.2%}"],
        ["Median Comment Ratio", f"{benchmarks.get('median_comment_ratio', 0):.3%}"],
        ["Avg View Velocity", f"{benchmarks.get('avg_view_velocity', 0):,.1f}/hr"],
        ["Best Duration", benchmarks.get("best_duration_bucket", "")],
        ["Best Publish Day", benchmarks.get("best_publish_day", "")],
        ["Best Publish Hour (UTC)", f"{benchmarks.get('best_publish_hour_utc', 0)}:00"],
        ["Best Title Pattern", benchmarks.get("best_title_pattern", "")],
    ]
    ws.update(rows, f"A2:B{len(rows) + 1}")
    print(f"  Summary: {len(rows)} rows")


def push_trending_topics(spreadsheet, data):
    """Push trending topics to a tab."""
    topics = data["trending_topics"]
    headers = ["Topic", "Video Count", "Total Views", "Avg Views", "Avg Velocity", "Score", "Trend"]
    ws = ensure_worksheet(spreadsheet, "Trending Topics", headers)

    rows = [
        [t["topic"].title(), t["video_count"], t["total_views"],
         t["avg_views"], t["avg_velocity"], t["score"], t["trend"]]
        for t in topics
    ]
    if rows:
        ws.update(rows, f"A2:G{len(rows) + 1}")
    print(f"  Trending Topics: {len(rows)} rows")


def push_top_videos(spreadsheet, data):
    """Push top videos to a tab."""
    videos = data["top_videos"]
    headers = ["Title", "Channel", "Views", "Likes", "Comments", "Like Ratio", "Duration (s)", "Published", "URL"]
    ws = ensure_worksheet(spreadsheet, "Top Videos", headers)

    rows = [
        [v["title"], v["channel"], v["views"], v["likes"], v["comments"],
         f"{v['like_ratio']:.2%}", v["duration_seconds"], v["published_at"], v["url"]]
        for v in videos
    ]
    if rows:
        ws.update(rows, f"A2:I{len(rows) + 1}")
    print(f"  Top Videos: {len(rows)} rows")


def push_top_channels(spreadsheet, data):
    """Push top channels to a tab."""
    channels = data["top_channels"]
    headers = ["Name", "Subscribers", "Videos in Dataset", "Avg Views", "Engagement Rate", "Total Views", "URL"]
    ws = ensure_worksheet(spreadsheet, "Top Channels", headers)

    rows = [
        [ch["name"], ch["subscriber_count"], ch["videos_in_dataset"],
         ch["avg_views"], f"{ch['engagement_rate']:.2%}",
         ch["total_views_in_dataset"], ch["url"]]
        for ch in channels
    ]
    if rows:
        ws.update(rows, f"A2:G{len(rows) + 1}")
    print(f"  Top Channels: {len(rows)} rows")


def push_benchmarks(spreadsheet, data):
    """Push benchmark breakdowns to a tab."""
    benchmarks = data["engagement_benchmarks"]
    headers = ["Category", "Bucket", "Avg Views"]
    ws = ensure_worksheet(spreadsheet, "Benchmarks", headers)

    rows = []
    for bucket, views in benchmarks.get("duration_breakdown", {}).items():
        rows.append(["Duration", bucket, round(views)])
    for day, views in benchmarks.get("day_breakdown", {}).items():
        rows.append(["Day of Week", day, round(views)])
    for pattern, views in benchmarks.get("pattern_breakdown", {}).items():
        rows.append(["Title Pattern", pattern.title(), round(views)])

    if rows:
        ws.update(rows, f"A2:C{len(rows) + 1}")
    print(f"  Benchmarks: {len(rows)} rows")


def push_opportunities(spreadsheet, data):
    """Push content opportunities to a tab."""
    opportunities = data["content_opportunities"]
    headers = ["Topic", "Reason", "Avg Views", "Suggested Angle"]
    ws = ensure_worksheet(spreadsheet, "Opportunities", headers)

    rows = [
        [opp["topic"].title(), opp["reason"], opp["avg_views"], opp["suggested_angle"]]
        for opp in opportunities
    ]
    if rows:
        ws.update(rows, f"A2:D{len(rows) + 1}")
    print(f"  Opportunities: {len(rows)} rows")


def main():
    if not INPUT_PATH.exists():
        print(f"ERROR: Input file not found: {INPUT_PATH}")
        print("Run the analyzer first: python tools/analyze_data.py")
        sys.exit(1)

    if not SPREADSHEET_ID:
        print("ERROR: GOOGLE_SHEETS_ID not set in .env")
        print("Create a Google Sheet and add its ID to .env:")
        print("  GOOGLE_SHEETS_ID=your_spreadsheet_id_here")
        print("\nThe spreadsheet ID is the long string in the URL:")
        print("  https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit")
        sys.exit(1)

    print("Google Sheets Pusher")
    print("-" * 50)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    gc = get_sheets_client()
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    print(f"Connected to: {spreadsheet.title}")

    print("\nPushing data...")
    push_summary(spreadsheet, data)
    push_trending_topics(spreadsheet, data)
    push_top_videos(spreadsheet, data)
    push_top_channels(spreadsheet, data)
    push_benchmarks(spreadsheet, data)
    push_opportunities(spreadsheet, data)

    print(f"\nData pushed successfully to Google Sheets!")
    print(f"  URL: https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}")


if __name__ == "__main__":
    main()
