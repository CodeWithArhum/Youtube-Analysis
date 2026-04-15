"""
YouTube AI Niche Report — Branded PDF Generator
Creates a professional dark-themed PDF report from analysis results.

Usage: python tools/build_pdf.py
Input: .tmp/analysis_results.json
Output: .tmp/ai_youtube_report.pdf
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / ".tmp" / "analysis_results.json"
OUTPUT_PATH = ROOT / ".tmp" / "ai_youtube_report.pdf"

# Brand color palette
BG = HexColor("#0A0A0A")
SURFACE = HexColor("#2A2A2A")
ACCENT = HexColor("#BED754")
ACCENT_DARK = HexColor("#8A9E3A")
ACCENT_LIGHT = HexColor("#D4EF6A")
TEXT_PRIMARY = HexColor("#FFFFFF")
TEXT_SECONDARY = HexColor("#F5F5F5")
TEXT_MUTED = HexColor("#999999")
ALERT = HexColor("#E8293A")

PAGE_W, PAGE_H = letter  # 612 x 792
MARGIN = 50


def draw_bg(c):
    """Fill page with dark background."""
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def draw_accent_bar(c, y, width=None, height=4):
    """Draw a thin accent bar."""
    c.setFillColor(ACCENT)
    c.rect(MARGIN, y, width or (PAGE_W - 2 * MARGIN), height, fill=1, stroke=0)


def draw_text(c, text, x, y, size=12, color=TEXT_PRIMARY, bold=False, align="left", max_width=None):
    """Draw text on the canvas."""
    font = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(font, size)
    c.setFillColor(color)
    if align == "center":
        c.drawCentredString(x, y, text)
    elif align == "right":
        c.drawRightString(x, y, text)
    else:
        if max_width:
            # Truncate if too long
            while c.stringWidth(text, font, size) > max_width and len(text) > 3:
                text = text[:-4] + "..."
        c.drawString(x, y, text)


def draw_card(c, x, y, w, h):
    """Draw a rounded surface card."""
    c.setFillColor(SURFACE)
    c.roundRect(x, y, w, h, 6, fill=1, stroke=0)


def draw_stat_card(c, x, y, w, h, value, label, value_color=ACCENT):
    """Draw a stat card with large value and small label."""
    draw_card(c, x, y, w, h)
    draw_text(c, str(value), x + w / 2, y + h - 28, size=22, color=value_color, bold=True, align="center")
    draw_text(c, label, x + w / 2, y + 12, size=8, color=TEXT_MUTED, align="center")


def draw_bar_chart(c, x, y, w, h, categories, values, bar_color=ACCENT, label_suffix=""):
    """Draw a simple horizontal bar chart."""
    if not values:
        return
    max_val = max(values) if max(values) > 0 else 1
    bar_count = len(categories)
    bar_height = min(18, (h - 20) / bar_count - 6)
    gap = 6

    for i, (cat, val) in enumerate(zip(categories, values)):
        bar_y = y + h - 20 - (i + 1) * (bar_height + gap)
        bar_w = (val / max_val) * (w - 120) if max_val > 0 else 0

        # Category label
        draw_text(c, cat[:16], x, bar_y + 4, size=8, color=TEXT_SECONDARY)

        # Bar
        bar_x = x + 100
        c.setFillColor(bar_color)
        c.roundRect(bar_x, bar_y, max(bar_w, 2), bar_height, 3, fill=1, stroke=0)

        # Value label
        val_text = f"{val:,.0f}{label_suffix}" if val >= 1 else f"{val:.1f}{label_suffix}"
        draw_text(c, val_text, bar_x + max(bar_w, 2) + 6, bar_y + 4, size=7, color=TEXT_MUTED)


def fmt_number(n):
    """Format a number for display (1.2M, 456K, etc.)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return f"{n:,}"


def build_title_page(c, summary):
    """Page 1: Title page."""
    draw_bg(c)

    # Top accent bar
    c.setFillColor(ACCENT)
    c.rect(0, PAGE_H - 6, PAGE_W, 6, fill=1, stroke=0)

    # Title
    draw_text(c, "AI YOUTUBE", PAGE_W / 2, PAGE_H - 200, size=42, color=TEXT_PRIMARY, bold=True, align="center")
    draw_text(c, "LANDSCAPE REPORT", PAGE_W / 2, PAGE_H - 250, size=42, color=ACCENT, bold=True, align="center")

    # Accent line
    draw_accent_bar(c, PAGE_H - 275, width=200, height=3)
    c.rect(PAGE_W / 2 - 100, PAGE_H - 275, 200, 3, fill=1, stroke=0)

    # Date range
    draw_text(c, f"Weekly Intelligence Report  |  {summary['date_range']}",
              PAGE_W / 2, PAGE_H - 310, size=14, color=TEXT_MUTED, align="center")

    # Stats bar
    stats_y = PAGE_H - 380
    stats = [
        (f"{summary['total_videos']}", "Videos Analyzed"),
        (f"{summary['unique_channels']}", "Channels Tracked"),
        (f"{fmt_number(summary['total_views'])}", "Total Views"),
    ]
    card_w = 140
    total_w = card_w * 3 + 20 * 2
    start_x = (PAGE_W - total_w) / 2
    for i, (val, label) in enumerate(stats):
        cx = start_x + i * (card_w + 20)
        draw_stat_card(c, cx, stats_y, card_w, 60, val, label)

    # Footer
    draw_text(c, "Powered by YouTube Data API v3 + AI Analysis",
              PAGE_W / 2, 60, size=9, color=TEXT_MUTED, align="center")

    c.showPage()


def build_executive_summary(c, summary, benchmarks):
    """Page 2: Executive Summary."""
    draw_bg(c)
    draw_text(c, "Executive Summary", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=160, height=3)

    # Stat cards row
    cards = [
        (f"{summary['total_videos']}", "Videos Analyzed", ACCENT),
        (f"{fmt_number(summary['avg_views'])}", "Average Views", ACCENT_LIGHT),
        (f"{fmt_number(summary['max_views'])}", "Top Video Views", ACCENT_DARK),
        (f"{summary['unique_channels']}", "Channels Tracked", ACCENT),
    ]
    card_w = (PAGE_W - 2 * MARGIN - 30) / 4
    for i, (val, label, color) in enumerate(cards):
        cx = MARGIN + i * (card_w + 10)
        draw_stat_card(c, cx, PAGE_H - 160, card_w, 65, val, label, color)

    # Key Findings
    draw_text(c, "Key Findings", MARGIN, PAGE_H - 200, size=16, color=TEXT_PRIMARY, bold=True)

    best_duration = benchmarks.get("best_duration_bucket", "N/A")
    best_day = benchmarks.get("best_publish_day", "N/A")
    dur_breakdown = benchmarks.get("duration_breakdown", {})
    day_breakdown = benchmarks.get("day_breakdown", {})

    # Calculate dynamic insights from data
    best_dur_views = dur_breakdown.get(best_duration, 0)
    worst_dur = min(dur_breakdown, key=dur_breakdown.get) if dur_breakdown else "N/A"
    worst_dur_views = dur_breakdown.get(worst_dur, 1)
    dur_ratio = best_dur_views / worst_dur_views if worst_dur_views > 0 else 0

    best_day_views = day_breakdown.get(best_day, 0)
    weekday_views = [v for d, v in day_breakdown.items() if d not in ("Saturday", "Sunday")]
    avg_weekday = sum(weekday_views) / len(weekday_views) if weekday_views else 1
    day_ratio = best_day_views / avg_weekday if avg_weekday > 0 else 0

    findings = [
        f"Short-form content ({best_duration}) dominates — {fmt_number(best_dur_views)} avg views vs {fmt_number(worst_dur_views)} for {worst_dur}",
        f"{best_day} is the best publish day — {fmt_number(best_day_views)} avg views, {day_ratio:.1f}x better than weekday avg",
        f"Median engagement: {benchmarks.get('median_like_ratio', 0):.1%} like ratio, {benchmarks.get('median_comment_ratio', 0):.2%} comment ratio",
        f"Average view velocity: {benchmarks.get('avg_view_velocity', 0):,.0f} views/hour across all tracked videos",
    ]

    y = PAGE_H - 230
    for finding in findings:
        # Bullet
        c.setFillColor(ACCENT)
        c.circle(MARGIN + 6, y + 4, 3, fill=1, stroke=0)
        draw_text(c, finding, MARGIN + 18, y, size=10, color=TEXT_SECONDARY, max_width=PAGE_W - 2 * MARGIN - 20)
        y -= 22

    # Summary stats table
    y -= 20
    draw_text(c, "Summary Statistics", MARGIN, y, size=16, color=TEXT_PRIMARY, bold=True)
    y -= 25

    table_data = [
        ("Total Videos", f"{summary['total_videos']}"),
        ("Unique Channels", f"{summary['unique_channels']}"),
        ("Total Views", f"{summary['total_views']:,}"),
        ("Average Views", f"{summary['avg_views']:,}"),
        ("Median Views", f"{summary['median_views']:,}"),
        ("Max Views", f"{summary['max_views']:,}"),
        ("Date Range", summary['date_range']),
    ]
    for label, value in table_data:
        draw_card(c, MARGIN, y - 4, PAGE_W - 2 * MARGIN, 20)
        draw_text(c, label, MARGIN + 10, y, size=9, color=TEXT_MUTED)
        draw_text(c, value, PAGE_W - MARGIN - 10, y, size=9, color=ACCENT, bold=True, align="right")
        y -= 26

    c.showPage()


def build_trending_topics(c, topics):
    """Page 3: Trending Topics."""
    draw_bg(c)
    draw_text(c, "Trending Topics", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=160, height=3)

    # Bar chart — top topics by total views
    chart_topics = [t["topic"].title() for t in topics[:10]]
    chart_views = [t["total_views"] / 1_000_000 for t in topics[:10]]
    draw_bar_chart(c, MARGIN, PAGE_H - 520, PAGE_W - 2 * MARGIN, 420,
                   chart_topics, chart_views, ACCENT, "M views")

    # Rising topics sidebar
    y = PAGE_H - 550
    draw_text(c, "Rising Topics", MARGIN, y, size=14, color=TEXT_PRIMARY, bold=True)
    y -= 20
    rising = [t for t in topics if t["trend"] == "rising"][:6]
    for t in rising:
        c.setFillColor(ACCENT_DARK)
        c.circle(MARGIN + 5, y + 3, 2.5, fill=1, stroke=0)
        text = f"{t['topic'].title()} — {t['video_count']} videos, {fmt_number(t['avg_views'])} avg views"
        draw_text(c, text, MARGIN + 14, y, size=8, color=TEXT_SECONDARY, max_width=PAGE_W - 2 * MARGIN - 20)
        y -= 16

    c.showPage()


def build_top_videos(c, top_videos):
    """Page 4: Top Performing Videos."""
    draw_bg(c)
    draw_text(c, "Top Performing Videos", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=200, height=3)

    y = PAGE_H - 110
    for i, v in enumerate(top_videos[:8]):
        card_h = 68
        draw_card(c, MARGIN, y - card_h + 15, PAGE_W - 2 * MARGIN, card_h)

        # Rank
        draw_text(c, f"#{i + 1}", MARGIN + 12, y, size=20, color=ACCENT, bold=True)

        # Title (truncated)
        title = v["title"]
        draw_text(c, title, MARGIN + 50, y, size=11, color=TEXT_PRIMARY, bold=True,
                  max_width=PAGE_W - 2 * MARGIN - 200)

        # Channel
        draw_text(c, f"by {v['channel']}", MARGIN + 50, y - 16, size=8, color=TEXT_MUTED)

        # Views
        draw_text(c, f"{v['views']:,} views", PAGE_W - MARGIN - 10, y,
                  size=11, color=ACCENT_LIGHT, bold=True, align="right")

        # Like ratio
        draw_text(c, f"{v['like_ratio']:.1%} likes", PAGE_W - MARGIN - 10, y - 16,
                  size=8, color=TEXT_MUTED, align="right")

        # Separator
        y -= card_h + 8

    c.showPage()


def build_top_channels(c, top_channels):
    """Page 5: Top Channels by Engagement."""
    draw_bg(c)
    draw_text(c, "Top Channels by Engagement", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=220, height=3)

    y = PAGE_H - 110
    for i, ch in enumerate(top_channels[:8]):
        card_h = 68
        draw_card(c, MARGIN, y - card_h + 15, PAGE_W - 2 * MARGIN, card_h)

        # Rank
        draw_text(c, f"#{i + 1}", MARGIN + 12, y, size=20, color=ACCENT, bold=True)

        # Name
        draw_text(c, ch["name"], MARGIN + 50, y, size=11, color=TEXT_PRIMARY, bold=True,
                  max_width=280)

        # Subscribers
        draw_text(c, f"{ch['subscriber_count']:,} subscribers", MARGIN + 50, y - 16,
                  size=8, color=TEXT_MUTED)

        # Engagement rate
        draw_text(c, f"{ch['engagement_rate']:.1%} engagement", PAGE_W - MARGIN - 10, y,
                  size=11, color=ACCENT_LIGHT, bold=True, align="right")

        # Avg views
        draw_text(c, f"{ch['avg_views']:,} avg views", PAGE_W - MARGIN - 10, y - 16,
                  size=8, color=TEXT_MUTED, align="right")

        y -= card_h + 8

    c.showPage()


def build_engagement_benchmarks(c, benchmarks):
    """Page 6: Engagement Benchmarks."""
    draw_bg(c)
    draw_text(c, "Engagement Benchmarks", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=200, height=3)

    # Stat cards
    cards = [
        (f"{benchmarks.get('median_like_ratio', 0):.1%}", "Median Like Ratio", ACCENT),
        (f"{benchmarks.get('median_comment_ratio', 0):.2%}", "Median Comment Ratio", ACCENT_LIGHT),
        (f"{benchmarks.get('avg_view_velocity', 0):,.0f}/hr", "Avg View Velocity", ACCENT_DARK),
        (benchmarks.get("best_duration_bucket", "N/A"), "Best Duration", ACCENT),
    ]
    card_w = (PAGE_W - 2 * MARGIN - 30) / 4
    for i, (val, label, color) in enumerate(cards):
        cx = MARGIN + i * (card_w + 10)
        draw_stat_card(c, cx, PAGE_H - 160, card_w, 65, val, label, color)

    # Duration breakdown chart
    dur_data = benchmarks.get("duration_breakdown", {})
    if dur_data:
        draw_text(c, "Average Views by Duration", MARGIN, PAGE_H - 195, size=12, color=TEXT_SECONDARY)
        cats = list(dur_data.keys())
        vals = [v / 1000 for v in dur_data.values()]
        draw_bar_chart(c, MARGIN, PAGE_H - 430, (PAGE_W - 2 * MARGIN - 20) / 2, 220,
                       cats, vals, ACCENT, "K")

    # Pattern breakdown chart
    pat_data = benchmarks.get("pattern_breakdown", {})
    if pat_data:
        chart_x = MARGIN + (PAGE_W - 2 * MARGIN) / 2 + 10
        draw_text(c, "Average Views by Title Pattern", chart_x, PAGE_H - 195, size=12, color=TEXT_SECONDARY)
        cats = [k.title() for k in pat_data.keys()]
        vals = [v / 1000 for v in pat_data.values()]
        draw_bar_chart(c, chart_x, PAGE_H - 430, (PAGE_W - 2 * MARGIN - 20) / 2, 220,
                       cats, vals, ACCENT_DARK, "K")

    c.showPage()


def build_publishing_strategy(c, benchmarks):
    """Page 7: Publishing Strategy."""
    draw_bg(c)
    draw_text(c, "Optimal Publishing Strategy", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=230, height=3)

    # Day of week chart
    day_data = benchmarks.get("day_breakdown", {})
    if day_data:
        draw_text(c, "Average Views by Publish Day", MARGIN, PAGE_H - 100, size=12, color=TEXT_SECONDARY)
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        ordered_days = [d for d in day_order if d in day_data]
        day_vals = [day_data[d] / 1000 for d in ordered_days]
        short_days = [d[:3] for d in ordered_days]
        draw_bar_chart(c, MARGIN, PAGE_H - 390, PAGE_W - 2 * MARGIN, 270,
                       short_days, day_vals, ACCENT_LIGHT, "K")

    # Key takeaways
    y = PAGE_H - 420
    draw_text(c, "Key Takeaways", MARGIN, y, size=16, color=TEXT_PRIMARY, bold=True)
    y -= 25

    pat_data = benchmarks.get("pattern_breakdown", {})
    sorted_patterns = sorted(pat_data.items(), key=lambda x: x[1], reverse=True)

    takeaways = [
        f"Best day: {benchmarks.get('best_publish_day', 'N/A')} ({fmt_number(day_data.get(benchmarks.get('best_publish_day', ''), 0))} avg views)",
        f"Best hour: {benchmarks.get('best_publish_hour_utc', 0)}:00 UTC",
        f"Best duration: {benchmarks.get('best_duration_bucket', 'N/A')}",
    ]
    for pattern, avg_views in sorted_patterns[:4]:
        takeaways.append(f"{pattern.title()} titles average {fmt_number(avg_views)} views")

    for takeaway in takeaways:
        c.setFillColor(ACCENT)
        c.circle(MARGIN + 6, y + 3, 3, fill=1, stroke=0)
        draw_text(c, takeaway, MARGIN + 18, y, size=10, color=TEXT_SECONDARY)
        y -= 20

    c.showPage()


def build_content_opportunities(c, opportunities):
    """Page 8: Content Opportunities."""
    draw_bg(c)
    draw_text(c, "Content Opportunities", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=190, height=3)

    y = PAGE_H - 110
    for i, opp in enumerate(opportunities[:7]):
        card_h = 62
        draw_card(c, MARGIN, y - card_h + 15, PAGE_W - 2 * MARGIN, card_h)

        # Topic
        draw_text(c, opp["topic"].title(), MARGIN + 12, y, size=13, color=ACCENT, bold=True)

        # Avg views
        draw_text(c, f"{opp['avg_views']:,} avg views", PAGE_W - MARGIN - 10, y,
                  size=11, color=ACCENT_LIGHT, bold=True, align="right")

        # Reason
        draw_text(c, opp["reason"], MARGIN + 12, y - 18, size=8, color=TEXT_MUTED,
                  max_width=PAGE_W - 2 * MARGIN - 30)

        y -= card_h + 8

    c.showPage()


def build_recommendations(c, benchmarks, topics, opportunities):
    """Page 9: Recommendations."""
    draw_bg(c)
    draw_text(c, "Recommendations", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=160, height=3)

    # Generate dynamic recommendations from data
    best_day = benchmarks.get("best_publish_day", "Saturday")
    best_duration = benchmarks.get("best_duration_bucket", "0-5min")
    day_breakdown = benchmarks.get("day_breakdown", {})
    dur_breakdown = benchmarks.get("duration_breakdown", {})
    pat_breakdown = benchmarks.get("pattern_breakdown", {})

    best_day_views = day_breakdown.get(best_day, 0)
    weekday_views = [v for d, v in day_breakdown.items() if d not in ("Saturday", "Sunday")]
    avg_weekday = sum(weekday_views) / len(weekday_views) if weekday_views else 1
    day_ratio = best_day_views / avg_weekday if avg_weekday > 0 else 0

    best_dur_views = dur_breakdown.get(best_duration, 0)
    worst_dur = min(dur_breakdown, key=dur_breakdown.get) if dur_breakdown else ""
    worst_dur_views = dur_breakdown.get(worst_dur, 1)
    dur_ratio = best_dur_views / worst_dur_views if worst_dur_views > 0 else 0

    sorted_patterns = sorted(pat_breakdown.items(), key=lambda x: x[1], reverse=True)
    top_patterns = [p[0] for p in sorted_patterns[:2]]
    bot_patterns = [p[0] for p in sorted_patterns[-2:]]

    top_opp = opportunities[0] if opportunities else None
    top_topic_names = [t["topic"].title() for t in topics[:3]]

    recs = [
        f"Publish on {best_day} for maximum reach — {day_ratio:.1f}x better than weekday average",
        f"Keep videos under {best_duration.replace('min', ' minutes')} — {dur_ratio:.1f}x more views than {worst_dur}",
    ]
    if top_patterns:
        recs.append(f"Use {' or '.join(top_patterns)} title formats — they outperform {' and '.join(bot_patterns)}")
    if top_opp:
        recs.append(f"Create content about {top_opp['topic'].title()} — {top_opp['reason']}")
    if top_topic_names:
        recs.append(f"Trending now: {', '.join(top_topic_names)} — ride the wave while velocity is high")
    recs.append(f"Post at {benchmarks.get('best_publish_hour_utc', 0)}:00 UTC for optimal visibility")

    y = PAGE_H - 110
    for i, rec in enumerate(recs):
        card_h = 52
        draw_card(c, MARGIN, y - card_h + 15, PAGE_W - 2 * MARGIN, card_h)

        # Number
        draw_text(c, str(i + 1), MARGIN + 16, y - 2, size=22, color=ACCENT, bold=True)

        # Recommendation text
        draw_text(c, rec, MARGIN + 46, y, size=10, color=TEXT_PRIMARY, max_width=PAGE_W - 2 * MARGIN - 60)

        y -= card_h + 8

    c.showPage()


def build_methodology(c, summary):
    """Page 10: Methodology."""
    draw_bg(c)
    draw_text(c, "Methodology", MARGIN, PAGE_H - 60, size=24, color=TEXT_PRIMARY, bold=True)
    draw_accent_bar(c, PAGE_H - 72, width=120, height=3)

    items = [
        ("Data Source", "YouTube Data API v3 via OAuth"),
        ("Date Range", summary["date_range"]),
        ("Search Keywords", "AI automation, artificial intelligence, AI tools, AI agents, AI workflow, AI tutorial, AI news"),
        ("Search Strategy", "14 searches (7 keywords x 2 sort orders: relevance, viewCount)"),
        ("Dataset", f"{summary['total_videos']} unique videos, {summary['unique_channels']} unique channels"),
        ("Metrics", "views, likes, comments, duration, publish timing, tags, title patterns"),
        ("Engagement Rate", "(likes + comments) / views"),
        ("View Velocity", "views / hours since publish"),
        ("Topic Scoring", "avg views x sqrt(video count)"),
    ]

    y = PAGE_H - 110
    for label, value in items:
        draw_card(c, MARGIN, y - 10, PAGE_W - 2 * MARGIN, 28)
        draw_text(c, label, MARGIN + 10, y - 2, size=9, color=ACCENT, bold=True)
        draw_text(c, value, MARGIN + 140, y - 2, size=9, color=TEXT_SECONDARY,
                  max_width=PAGE_W - MARGIN - 160)
        y -= 36

    # Footer
    generated = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")
    draw_text(c, f"Generated on {generated}", PAGE_W / 2, 80, size=9,
              color=TEXT_MUTED, align="center")
    draw_text(c, "YouTube AI Niche Analysis Automation", PAGE_W / 2, 64, size=9,
              color=TEXT_MUTED, align="center")

    # Bottom accent bar
    c.setFillColor(ACCENT)
    c.rect(0, 0, PAGE_W, 4, fill=1, stroke=0)

    c.showPage()


def build_report(data: dict) -> str:
    """Build the full branded PDF report."""
    summary = data["summary"]
    topics = data["trending_topics"]
    top_videos = data["top_videos"]
    top_channels = data["top_channels"]
    benchmarks = data["engagement_benchmarks"]
    opportunities = data["content_opportunities"]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(OUTPUT_PATH), pagesize=letter)
    c.setTitle("AI YouTube Landscape Report")
    c.setAuthor("YouTube AI Analysis Automation")

    build_title_page(c, summary)
    build_executive_summary(c, summary, benchmarks)
    build_trending_topics(c, topics)
    build_top_videos(c, top_videos)
    build_top_channels(c, top_channels)
    build_engagement_benchmarks(c, benchmarks)
    build_publishing_strategy(c, benchmarks)
    build_content_opportunities(c, opportunities)
    build_recommendations(c, benchmarks, topics, opportunities)
    build_methodology(c, summary)

    c.save()
    return str(OUTPUT_PATH)


def main():
    if not INPUT_PATH.exists():
        print(f"ERROR: Input file not found: {INPUT_PATH}")
        print("Run the analyzer first: python tools/analyze_data.py")
        sys.exit(1)

    print("Building AI YouTube Report (PDF)...")
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    output = build_report(data)
    print(f"PDF report saved to: {output}")


if __name__ == "__main__":
    main()
