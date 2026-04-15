# Workflow: Build & Deliver Report

## Objective
Create a branded PDF report from analysis results, push data to Google Sheets, and email the report via Gmail.

## Required Inputs
- `.tmp/analysis_results.json` (output of the analyzer)
- OAuth client secret JSON file in project root
- `GOOGLE_SHEETS_ID` set in `.env`
- Gmail OAuth token (or first-time browser auth)

## Tools
- `tools/build_pdf.py` — generates branded PDF report
- `tools/push_to_sheets.py` — pushes analysis summary to Google Sheets
- `tools/send_email.py` — emails the PDF report via Gmail

## Steps

### Step 1: Build PDF Report
```bash
python tools/build_pdf.py
```
Reads `.tmp/analysis_results.json` and generates `.tmp/ai_youtube_report.pdf` with:
- 10 pages: Title, Executive Summary, Trending Topics, Top Videos, Top Channels, Engagement Benchmarks, Publishing Strategy, Content Opportunities, Recommendations, Methodology
- Brand colors: dark background (#0A0A0A), green accent (#BED754), white text
- Dynamic insights computed from the data (not hardcoded)

### Step 2: Push to Google Sheets
```bash
python tools/push_to_sheets.py
```
Pushes analysis data to 6 tabs in the configured Google Sheet:
- Summary, Trending Topics, Top Videos, Top Channels, Benchmarks, Opportunities
- Clears and rewrites each tab on every run

### Step 3: Send via Gmail
```bash
python tools/send_email.py
```
Sends the PDF report as an email attachment to the authenticated user's Gmail.

## Expected Output
- `.tmp/ai_youtube_report.pdf` — branded 10-page PDF report
- Google Sheets updated with latest analysis data
- Email delivered with PDF attachment

## Edge Cases
- **Missing analysis data:** All tools check for `.tmp/analysis_results.json` and exit with instructions
- **Google Sheets ID not set:** `push_to_sheets.py` prints setup instructions
- **OAuth token expired:** Auto-refreshes; if refresh fails, opens browser for re-auth
- **Empty data sections:** Charts and lists gracefully handle empty arrays
