# Workflow: Scrape YouTube Data

## Objective
Collect video and channel data from YouTube's AI/AI automation niche for trend analysis.

## Required Inputs
- `YOUTUBE_API_KEY` set in `.env`

## Tool
`tools/youtube_scraper.py`

## Run Command
```bash
python tools/youtube_scraper.py
```

## What It Does
1. Searches YouTube for 7 AI-related keywords × 2 sort orders (relevance, viewCount)
2. Deduplicates video IDs across all searches
3. Fetches detailed stats for each video (views, likes, comments, duration, tags)
4. Fetches channel stats for each unique channel (subscribers, total views, video count)
5. Saves everything to `.tmp/raw_youtube_data.json`

## Search Keywords
- AI automation, artificial intelligence, AI tools, AI agents, AI workflow, AI tutorial, AI news

## Expected Output
`.tmp/raw_youtube_data.json` containing:
- `videos[]` — array of video objects with stats
- `channels[]` — array of channel objects with stats
- `scraped_at` — timestamp of the scrape
- `date_range` — rolling 7-day window

## Quota Usage
~1,430 units per run (daily limit is 10,000)

## Edge Cases
- **Quota exceeded (403):** Script saves partial data and exits gracefully. Re-run the next day.
- **Rate limited (429):** Automatic retry with exponential backoff (3 attempts).
- **Bad request (400):** Skips that keyword search, continues with the rest.
- **No API key:** Script prints setup instructions and exits.

## Customization
Edit `SEARCH_KEYWORDS` and `LOOKBACK_DAYS` in the script to adjust the search scope.
