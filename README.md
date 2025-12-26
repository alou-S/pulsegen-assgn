# B2B Scraper

A simple CLI tool to scrape B2B product reviews from **G2** and **Capterra**.

## Features

- 🔍 Search for products by name
- 📅 Filter reviews by date range
- 🤖 Automatic CAPTCHA detection (manual solve required)
- 💾 Export reviews to JSON
- 🖥️ Interactive TUI mode or simple CLI arguments for scripting


## Sample Output Files

- [g2-visual-studio-2025-12-20-to-2025-12-26.json](g2-visual-studio-2025-08-10-to-2025-12-10.json) - G2 reviews for Visual Studio
- [capterra-visual-studio-code-2025-10-20-to-2025-12-26.json](capterra-visual-studio-code-2025-08-10-to-2025-12-10.json) - Capterra reviews for Visual Studio Code

## To Be Improved

- 🤖 **Bot Detection on G2**: G2 often triggers bot verification challenges when excessive scraping is detected, which can interrupt the scraping process and require manual intervention.

- 🔧 **Third-Party Scraping Services**: Tools like [Firecrawl](https://firecrawl.dev), [ScrapingBee](https://scrapingbee.com), or [ScraperAPI](https://scraperapi.com) could help bypass anti-bot measures and improve reliability. However, to keep this project simple and dependency-free, these services were not integrated.

- ⚡ **Rate Limiting**: Implementing smarter rate limiting and request delays could help reduce bot detection triggers. Also implement better bot detection evasion.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### CLI Mode

```
usage: main.py [-h] [--product PRODUCT] [--start-date START_DATE] [--end-date END_DATE] [--source {g2,capterra}]

Scrape B2B reviews for a product

options:
  -h, --help            show this help message and exit
  --product PRODUCT     Product name to search
  --start-date START_DATE
                        Start date (YYYY-MM-DD)
  --end-date END_DATE   End date (YYYY-MM-DD)
  --source {g2,capterra}
                        Source platform (g2 or capterra)
```

**Example:**

```bash
python main.py --product "Visual Studio Code" --start-date 2025-10-20 --end-date 2025-12-26 --source g2
```

### Interactive Mode

Simply run without arguments:

```bash
python main.py
```

You'll be prompted to:
1. Select a source platform (G2 or Capterra)
2. Enter product name
3. Select from search results (if no exact match)
4. Enter date range

## Output

Reviews are saved as JSON files with the naming convention:

```
{source}-{product_name}-{start_date}-to-{end_date}.json
```

## Requirements

- Python 3.8+
- Chrome browser

## Notes

- A Chrome profile is stored locally in `chrome_profile/` for persistent sessions
- If CAPTCHA is detected, you'll need to solve it manually in the browser window
- Reviews are sorted by most recent and filtered by date range
