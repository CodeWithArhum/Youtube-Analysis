"""
YouTube AI Niche Analyzer
Processes raw YouTube data into actionable insights for reporting.

Usage: python tools/analyze_data.py
Input: .tmp/raw_youtube_data.json
Output: .tmp/analysis_results.json
"""

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / ".tmp" / "raw_youtube_data.json"
OUTPUT_PATH = ROOT / ".tmp" / "analysis_results.json"

# Common English stop words to filter from topic extraction
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "it", "this", "that", "are", "was", "be",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "not", "no", "so", "if", "then",
    "than", "too", "very", "just", "about", "up", "out", "how", "what",
    "when", "where", "who", "which", "why", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "only",
    "own", "same", "into", "over", "after", "before", "between",
    "under", "again", "further", "once", "here", "there", "from",
    "been", "being", "were", "they", "them", "their", "its", "my",
    "your", "our", "his", "her", "we", "you", "i", "me", "us", "he",
    "she", "him", "get", "got", "make", "made", "like", "use", "used",
    "using", "new", "one", "two", "also", "way", "well", "back",
    "even", "want", "because", "any", "these", "give", "day", "don",
    "don't", "won't", "can't", "doesn't", "didn't", "isn't", "aren't",
    "let", "know", "need", "think", "see", "come", "take", "going",
    "still", "much", "many", "really", "right", "now", "thing",
    "things", "video", "videos", "watch", "subscribe", "channel",
}


def load_raw_data(path: Path) -> dict:
    """Load the raw scraped YouTube data."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def hours_since_publish(published_at: str) -> float:
    """Calculate hours elapsed since a video was published."""
    try:
        pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - pub_time
        return max(delta.total_seconds() / 3600, 1)  # minimum 1 hour
    except (ValueError, AttributeError):
        return 1


def extract_topics(videos: list[dict]) -> list[dict]:
    """
    Extract trending topics from video titles and tags.
    Score = sum(view_count) / count(videos) for each keyword.
    """
    keyword_views = Counter()
    keyword_counts = Counter()
    keyword_velocity = Counter()
    keyword_velocity_counts = Counter()

    for video in videos:
        # Combine title words and tags
        title_words = re.findall(r"[a-zA-Z]+(?:\s[a-zA-Z]+)?", video["title"].lower())
        tags = [t.lower() for t in video.get("tags", [])]
        all_keywords = set()

        # Extract meaningful phrases from title
        for word in title_words:
            word = word.strip()
            if word and word not in STOP_WORDS and len(word) > 2:
                all_keywords.add(word)

        # Add tags
        for tag in tags:
            tag = tag.strip()
            if tag and tag not in STOP_WORDS and len(tag) > 2:
                all_keywords.add(tag)

        views = video.get("view_count", 0)
        velocity = views / hours_since_publish(video.get("published_at", ""))

        for kw in all_keywords:
            keyword_views[kw] += views
            keyword_counts[kw] += 1
            keyword_velocity[kw] += velocity
            keyword_velocity_counts[kw] += 1

    # Score and rank topics (minimum 3 videos to count)
    topics = []
    for kw in keyword_counts:
        if keyword_counts[kw] < 3:
            continue
        avg_views = keyword_views[kw] / keyword_counts[kw]
        avg_velocity = keyword_velocity[kw] / keyword_velocity_counts[kw]
        topics.append(
            {
                "topic": kw,
                "video_count": keyword_counts[kw],
                "total_views": keyword_views[kw],
                "avg_views": round(avg_views),
                "avg_velocity": round(avg_velocity, 1),
                "score": round(avg_views * (keyword_counts[kw] ** 0.5), 1),
                "trend": "rising" if avg_velocity > 500 else "stable",
            }
        )

    topics.sort(key=lambda x: x["score"], reverse=True)
    return topics[:15]


def rank_channels(videos: list[dict], channels: list[dict]) -> list[dict]:
    """Rank channels by engagement rate and average views."""
    channel_map = {c["channel_id"]: c for c in channels}

    # Aggregate video stats per channel
    channel_stats = {}
    for video in videos:
        cid = video["channel_id"]
        if cid not in channel_stats:
            channel_stats[cid] = {
                "video_ids": [],
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
            }
        stats = channel_stats[cid]
        stats["video_ids"].append(video["video_id"])
        stats["total_views"] += video.get("view_count", 0)
        stats["total_likes"] += video.get("like_count", 0)
        stats["total_comments"] += video.get("comment_count", 0)

    ranked = []
    for cid, stats in channel_stats.items():
        channel_info = channel_map.get(cid, {})
        total_views = stats["total_views"]
        num_videos = len(stats["video_ids"])

        if total_views == 0:
            continue

        engagement_rate = (stats["total_likes"] + stats["total_comments"]) / total_views
        avg_views = total_views / num_videos

        ranked.append(
            {
                "channel_id": cid,
                "name": channel_info.get("title", "Unknown"),
                "custom_url": channel_info.get("custom_url", ""),
                "subscriber_count": channel_info.get("subscriber_count", 0),
                "videos_in_dataset": num_videos,
                "avg_views": round(avg_views),
                "engagement_rate": round(engagement_rate, 4),
                "total_views_in_dataset": total_views,
                "url": f"https://youtube.com/{channel_info.get('custom_url', '')}",
            }
        )

    ranked.sort(key=lambda x: x["engagement_rate"], reverse=True)
    return ranked[:10]


def classify_title_pattern(title: str) -> str:
    """Classify a video title into a content pattern."""
    lower = title.lower()
    if lower.startswith("how to") or lower.startswith("how i"):
        return "how-to"
    if re.search(r"top \d+|best \d+|\d+ best|\d+ ways", lower):
        return "listicle"
    if lower.rstrip().endswith("?") or lower.startswith(("what ", "why ", "is ", "can ", "should ", "will ", "does ")):
        return "question"
    if any(word in lower for word in ["breaking", "just released", "announced", "launches", "new release", "update"]):
        return "news"
    if "vs" in lower or "versus" in lower or "compared" in lower:
        return "comparison"
    if "tutorial" in lower or "step by step" in lower or "beginner" in lower or "guide" in lower:
        return "tutorial"
    return "other"


def compute_engagement_benchmarks(videos: list[dict]) -> dict:
    """Compute engagement benchmarks across all videos."""
    if not videos:
        return {}

    like_ratios = []
    comment_ratios = []
    velocities = []
    duration_buckets = {"0-5min": [], "5-10min": [], "10-20min": [], "20-30min": [], "30+min": []}
    day_views = {}  # day_of_week -> [views]
    hour_views = {}  # hour -> [views]
    pattern_stats = {}  # pattern -> [views]

    for video in videos:
        views = video.get("view_count", 0)
        if views == 0:
            continue

        likes = video.get("like_count", 0)
        comments = video.get("comment_count", 0)
        duration = video.get("duration_seconds", 0)
        published = video.get("published_at", "")

        like_ratios.append(likes / views)
        comment_ratios.append(comments / views)
        velocities.append(views / hours_since_publish(published))

        # Duration buckets
        minutes = duration / 60
        if minutes <= 5:
            bucket = "0-5min"
        elif minutes <= 10:
            bucket = "5-10min"
        elif minutes <= 20:
            bucket = "10-20min"
        elif minutes <= 30:
            bucket = "20-30min"
        else:
            bucket = "30+min"
        duration_buckets[bucket].append(views)

        # Day of week and hour
        try:
            pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            day_name = pub_dt.strftime("%A")
            hour = pub_dt.hour

            day_views.setdefault(day_name, []).append(views)
            hour_views.setdefault(hour, []).append(views)
        except (ValueError, AttributeError):
            pass

        # Title pattern
        pattern = classify_title_pattern(video.get("title", ""))
        pattern_stats.setdefault(pattern, []).append(views)

    # Find best duration bucket
    bucket_avgs = {}
    for bucket, views_list in duration_buckets.items():
        if views_list:
            bucket_avgs[bucket] = mean(views_list)
    best_duration = max(bucket_avgs, key=bucket_avgs.get) if bucket_avgs else "unknown"

    # Find best publish day
    day_avgs = {day: mean(v) for day, v in day_views.items() if v}
    best_day = max(day_avgs, key=day_avgs.get) if day_avgs else "unknown"

    # Find best publish hour
    hour_avgs = {h: mean(v) for h, v in hour_views.items() if v}
    best_hour = max(hour_avgs, key=hour_avgs.get) if hour_avgs else 0

    # Find best title pattern
    pattern_avgs = {p: mean(v) for p, v in pattern_stats.items() if v}
    best_pattern = max(pattern_avgs, key=pattern_avgs.get) if pattern_avgs else "other"

    return {
        "median_like_ratio": round(median(like_ratios), 4) if like_ratios else 0,
        "median_comment_ratio": round(median(comment_ratios), 4) if comment_ratios else 0,
        "avg_view_velocity": round(mean(velocities), 1) if velocities else 0,
        "best_duration_bucket": best_duration,
        "duration_breakdown": {k: round(v, 0) for k, v in bucket_avgs.items()},
        "best_publish_day": best_day,
        "day_breakdown": {k: round(v, 0) for k, v in day_avgs.items()},
        "best_publish_hour_utc": best_hour,
        "best_title_pattern": best_pattern,
        "pattern_breakdown": {k: round(v, 0) for k, v in pattern_avgs.items()},
    }


def identify_opportunities(
    topics: list[dict], benchmarks: dict, videos: list[dict]
) -> list[dict]:
    """Identify content opportunities based on analysis."""
    opportunities = []

    # Rising topics with high velocity
    for topic in topics:
        if topic["trend"] == "rising" and topic["video_count"] < 20:
            opportunities.append(
                {
                    "topic": topic["topic"],
                    "reason": f"Rising trend with only {topic['video_count']} videos — low competition, high velocity",
                    "avg_views": topic["avg_views"],
                    "suggested_angle": f"Create a comprehensive guide or tutorial about {topic['topic']}",
                }
            )

    # High-engagement format + underused topics
    best_pattern = benchmarks.get("best_title_pattern", "other")
    if best_pattern != "other":
        pattern_topics = [t for t in topics[:5] if t["trend"] == "rising"]
        for t in pattern_topics[:3]:
            opportunities.append(
                {
                    "topic": t["topic"],
                    "reason": f"'{best_pattern}' format performs best — apply it to trending topic '{t['topic']}'",
                    "avg_views": t["avg_views"],
                    "suggested_angle": f"Create a {best_pattern} video about {t['topic']}",
                }
            )

    return opportunities[:10]


def main():
    if not INPUT_PATH.exists():
        print(f"ERROR: Input file not found: {INPUT_PATH}")
        print("Run the scraper first: python tools/youtube_scraper.py")
        sys.exit(1)

    print("YouTube AI Niche Analyzer")
    print("-" * 50)

    data = load_raw_data(INPUT_PATH)
    videos = data.get("videos", [])
    channels = data.get("channels", [])

    if not videos:
        print("ERROR: No videos found in raw data.")
        sys.exit(1)

    print(f"Loaded {len(videos)} videos and {len(channels)} channels")
    print(f"Date range: {data.get('date_range', {}).get('from')} to {data.get('date_range', {}).get('to')}")

    # Summary stats
    view_counts = [v["view_count"] for v in videos if v.get("view_count", 0) > 0]
    summary = {
        "total_videos": len(videos),
        "unique_channels": len(channels),
        "date_range": f"{data['date_range']['from']} to {data['date_range']['to']}",
        "avg_views": round(mean(view_counts)) if view_counts else 0,
        "median_views": round(median(view_counts)) if view_counts else 0,
        "max_views": max(view_counts) if view_counts else 0,
        "total_views": sum(view_counts),
    }
    print(f"\nSummary: avg={summary['avg_views']:,} | median={summary['median_views']:,} | max={summary['max_views']:,}")

    # Trending topics
    print("\nExtracting trending topics...")
    trending_topics = extract_topics(videos)
    print(f"  Found {len(trending_topics)} trending topics")
    for t in trending_topics[:5]:
        print(f"    - {t['topic']} (score: {t['score']:,.0f}, {t['video_count']} videos, {t['trend']})")

    # Top videos
    top_videos = sorted(videos, key=lambda v: v.get("view_count", 0), reverse=True)[:10]
    top_videos_formatted = []
    for v in top_videos:
        like_ratio = v["like_count"] / v["view_count"] if v["view_count"] > 0 else 0
        top_videos_formatted.append(
            {
                "title": v["title"],
                "channel": v["channel_title"],
                "views": v["view_count"],
                "likes": v["like_count"],
                "comments": v["comment_count"],
                "like_ratio": round(like_ratio, 4),
                "duration_seconds": v["duration_seconds"],
                "published_at": v["published_at"],
                "url": f"https://youtube.com/watch?v={v['video_id']}",
            }
        )
    print(f"\nTop video: {top_videos[0]['title']} ({top_videos[0]['view_count']:,} views)")

    # Top channels
    print("\nRanking channels...")
    top_channels = rank_channels(videos, channels)
    print(f"  Top {len(top_channels)} channels by engagement")

    # Engagement benchmarks
    print("\nComputing engagement benchmarks...")
    benchmarks = compute_engagement_benchmarks(videos)
    print(f"  Median like ratio: {benchmarks.get('median_like_ratio', 0):.2%}")
    print(f"  Best duration: {benchmarks.get('best_duration_bucket', 'unknown')}")
    print(f"  Best day: {benchmarks.get('best_publish_day', 'unknown')}")
    print(f"  Best title pattern: {benchmarks.get('best_title_pattern', 'unknown')}")

    # Content opportunities
    print("\nIdentifying content opportunities...")
    opportunities = identify_opportunities(trending_topics, benchmarks, videos)
    print(f"  Found {len(opportunities)} opportunities")

    # Save results
    results = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_file": str(INPUT_PATH),
        "summary": summary,
        "trending_topics": trending_topics,
        "top_videos": top_videos_formatted,
        "top_channels": top_channels,
        "engagement_benchmarks": benchmarks,
        "content_opportunities": opportunities,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nAnalysis saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
