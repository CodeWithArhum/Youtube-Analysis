# Workflow: Analyze YouTube Data

## Objective
Process raw YouTube data into actionable insights: trending topics, top channels, engagement benchmarks, and content opportunities.

## Required Inputs
- `.tmp/raw_youtube_data.json` (output of the scraper)

## Tool
`tools/analyze_data.py`

## Run Command
```bash
python tools/analyze_data.py
```

## What It Computes

### Trending Topics
- Extracts keywords from video titles and tags
- Scores by: avg views × sqrt(video count)
- Flags "rising" topics based on view velocity (views/hour)
- Returns top 15 topics

### Top Channels
- Ranks by engagement rate: (likes + comments) / views
- Includes avg views per video, subscriber count, videos in dataset
- Returns top 10

### Engagement Benchmarks
- Median like-to-view ratio
- Median comment-to-view ratio
- Best performing duration bucket (0-5min, 5-10min, 10-20min, 20-30min, 30+min)
- Best publish day of week
- Best publish hour (UTC)
- Best title pattern (how-to, listicle, question, news, comparison, tutorial)

### Content Opportunities
- Rising topics with low competition (few videos)
- Best-performing format applied to trending topics
- Returns up to 10 actionable suggestions

## Expected Output
`.tmp/analysis_results.json` with sections: `summary`, `trending_topics`, `top_videos`, `top_channels`, `engagement_benchmarks`, `content_opportunities`

## Edge Cases
- **No input file:** Prints error and instructs to run scraper first.
- **Empty data:** Exits with error message.
