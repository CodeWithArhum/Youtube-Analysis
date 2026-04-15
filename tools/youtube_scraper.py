"""
YouTube AI Niche Scraper
Connects to YouTube Data API v3 to collect video and channel data
for AI/AI automation content analysis.

Usage: python tools/youtube_scraper.py
Requires: OAuth client secret JSON file in project root OR YOUTUBE_API_KEY in .env
Output: .tmp/raw_youtube_data.json
"""

import glob
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Project root
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Config
API_KEY = os.getenv("YOUTUBE_API_KEY")
OUTPUT_PATH = ROOT / ".tmp" / "raw_youtube_data.json"
TOKEN_PATH = ROOT / "token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

SEARCH_KEYWORDS = [
    "AI automation",
    "artificial intelligence",
    "AI tools",
    "AI agents",
    "AI workflow",
    "AI tutorial",
    "AI news",
]

SORT_ORDERS = ["relevance", "viewCount"]
MAX_RESULTS_PER_SEARCH = 50
LOOKBACK_DAYS = 7


def find_client_secret():
    """Find the OAuth client secret JSON file in the project root."""
    patterns = [
        str(ROOT / "client_secret*.json"),
        str(ROOT / "credentials.json"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
    return None


def build_youtube_client_oauth(client_secret_path: str):
    """Build YouTube client using OAuth (opens browser for first-time auth)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None

    # Load existing token if available
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("Opening browser for Google sign-in...")
            print("(Authorize the app to access YouTube data)")
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for future runs
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print("Token saved for future use.")

    return build("youtube", "v3", credentials=creds)


def build_youtube_client(api_key: str = None):
    """
    Build YouTube client. Tries OAuth first (client secret file),
    falls back to API key from .env.
    """
    client_secret = find_client_secret()

    if client_secret:
        print(f"Using OAuth: {Path(client_secret).name}")
        return build_youtube_client_oauth(client_secret)

    if api_key:
        print("Using API key from .env")
        return build("youtube", "v3", developerKey=api_key)

    return None


def parse_duration(iso_duration: str) -> int:
    """Convert ISO 8601 duration (PT10M30S) to total seconds."""
    match = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration or ""
    )
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def search_videos(
    youtube, keyword: str, order: str, published_after: str
) -> list[dict]:
    """
    Search for videos matching a keyword.
    Returns list of {video_id, channel_id} dicts.
    """
    results = []
    page_token = None

    try:
        request = youtube.search().list(
            part="snippet",
            q=keyword,
            type="video",
            order=order,
            publishedAfter=published_after,
            maxResults=MAX_RESULTS_PER_SEARCH,
            pageToken=page_token,
        )
        response = _execute_with_retry(request)

        for item in response.get("items", []):
            results.append(
                {
                    "video_id": item["id"]["videoId"],
                    "channel_id": item["snippet"]["channelId"],
                }
            )
    except HttpError as e:
        status = e.resp.status
        if status == 403:
            print(f"  [QUOTA] Quota exceeded during search for '{keyword}' ({order}). Stopping searches.")
            raise
        elif status == 400:
            print(f"  [SKIP] Bad request for '{keyword}' ({order}): {e}")
        else:
            print(f"  [ERROR] HTTP {status} for '{keyword}' ({order}): {e}")

    return results


def get_video_details(youtube, video_ids: list[str]) -> list[dict]:
    """Fetch detailed stats for videos in batches of 50."""
    videos = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        try:
            request = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch),
            )
            response = _execute_with_retry(request)

            for item in response.get("items", []):
                snippet = item["snippet"]
                stats = item.get("statistics", {})
                content = item.get("contentDetails", {})
                thumbnails = snippet.get("thumbnails", {})
                thumb_url = (
                    thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url", "")
                )

                videos.append(
                    {
                        "video_id": item["id"],
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "tags": snippet.get("tags", []),
                        "published_at": snippet.get("publishedAt", ""),
                        "channel_id": snippet.get("channelId", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                        "category_id": snippet.get("categoryId", ""),
                        "view_count": int(stats.get("viewCount", 0)),
                        "like_count": int(stats.get("likeCount", 0)),
                        "comment_count": int(stats.get("commentCount", 0)),
                        "duration_seconds": parse_duration(
                            content.get("duration", "")
                        ),
                        "thumbnail_url": thumb_url,
                    }
                )
        except HttpError as e:
            print(f"  [ERROR] Failed to fetch video details batch: {e}")

    return videos


def get_channel_details(youtube, channel_ids: list[str]) -> list[dict]:
    """Fetch channel stats in batches of 50."""
    channels = []

    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i : i + 50]
        try:
            request = youtube.channels().list(
                part="snippet,statistics",
                id=",".join(batch),
            )
            response = _execute_with_retry(request)

            for item in response.get("items", []):
                snippet = item["snippet"]
                stats = item.get("statistics", {})
                thumbnails = snippet.get("thumbnails", {})
                thumb_url = (
                    thumbnails.get("high", {}).get("url")
                    or thumbnails.get("medium", {}).get("url")
                    or thumbnails.get("default", {}).get("url", "")
                )

                channels.append(
                    {
                        "channel_id": item["id"],
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "custom_url": snippet.get("customUrl", ""),
                        "country": snippet.get("country", ""),
                        "thumbnail_url": thumb_url,
                        "subscriber_count": int(
                            stats.get("subscriberCount", 0)
                        ),
                        "total_view_count": int(stats.get("viewCount", 0)),
                        "video_count": int(stats.get("videoCount", 0)),
                        "hidden_subscriber_count": stats.get(
                            "hiddenSubscriberCount", False
                        ),
                    }
                )
        except HttpError as e:
            print(f"  [ERROR] Failed to fetch channel details batch: {e}")

    return channels


def _execute_with_retry(request, max_retries: int = 5):
    """Execute an API request with exponential backoff for rate limits and network errors."""
    for attempt in range(max_retries):
        try:
            return request.execute()
        except HttpError as e:
            if e.resp.status in (429, 500, 503) and attempt < max_retries - 1:
                wait = 2**attempt
                print(f"  [HTTP {e.resp.status}] Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
        except (ConnectionError, ConnectionResetError, OSError) as e:
            if attempt < max_retries - 1:
                wait = 2**attempt
                print(f"  [NETWORK] {type(e).__name__}, retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    return {}


def main():
    # Ensure output directory exists
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    youtube = build_youtube_client(API_KEY)

    if youtube is None:
        print("ERROR: No authentication method found.")
        print("Either:")
        print("  1. Place a client_secret*.json file in the project root (OAuth)")
        print("  2. Add YOUTUBE_API_KEY=your_key to .env")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    published_after = (now - timedelta(days=LOOKBACK_DAYS)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    date_from = (now - timedelta(days=LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    date_to = now.strftime("%Y-%m-%d")

    print(f"YouTube AI Niche Scraper")
    print(f"Date range: {date_from} to {date_to}")
    print(f"Keywords: {len(SEARCH_KEYWORDS)} | Sort orders: {len(SORT_ORDERS)}")
    print(f"Total searches: {len(SEARCH_KEYWORDS) * len(SORT_ORDERS)}")
    print("-" * 50)

    # Step 1: Search for videos
    all_video_ids = set()
    all_channel_ids = set()
    quota_exceeded = False

    for keyword in SEARCH_KEYWORDS:
        if quota_exceeded:
            break
        for order in SORT_ORDERS:
            if quota_exceeded:
                break
            print(f"Searching: '{keyword}' (sort: {order})...")
            try:
                results = search_videos(youtube, keyword, order, published_after)
                new_videos = 0
                for r in results:
                    if r["video_id"] not in all_video_ids:
                        new_videos += 1
                    all_video_ids.add(r["video_id"])
                    all_channel_ids.add(r["channel_id"])
                print(f"  Found {len(results)} results ({new_videos} new)")
            except HttpError:
                quota_exceeded = True
                print("  Stopping all searches due to quota limit.")

    print(f"\nTotal unique videos: {len(all_video_ids)}")
    print(f"Total unique channels: {len(all_channel_ids)}")

    # Step 2: Get video details
    print(f"\nFetching video details ({len(all_video_ids)} videos)...")
    videos = get_video_details(youtube, list(all_video_ids))
    print(f"  Retrieved details for {len(videos)} videos")

    # Step 3: Get channel details
    print(f"\nFetching channel details ({len(all_channel_ids)} channels)...")
    channels = get_channel_details(youtube, list(all_channel_ids))
    print(f"  Retrieved details for {len(channels)} channels")

    # Step 4: Save results
    output = {
        "scraped_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "search_keywords": SEARCH_KEYWORDS,
        "date_range": {"from": date_from, "to": date_to},
        "total_searches": len(SEARCH_KEYWORDS) * len(SORT_ORDERS),
        "quota_exceeded": quota_exceeded,
        "videos": videos,
        "channels": channels,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to {OUTPUT_PATH}")
    print(f"  Videos: {len(videos)}")
    print(f"  Channels: {len(channels)}")


if __name__ == "__main__":
    main()
