"""
B2B Review Scraper

A CLI tool for scraping product reviews from G2 and Capterra platforms.
Supports both interactive mode and command-line arguments.
"""

import os
import argparse
import sys
import undetected_chromedriver as uc
import questionary
import json
from src.g2_search import g2_search
from src.g2_scrape import g2_scrape
from src.capterra_search import capterra_search
from src.capterra_scrape import capterra_scrape
from src.utils import validate_date_range


def main():
    """
    Main entry point for the review scraper.

    Supports two modes:
    - CLI mode: All arguments provided via command line
    - Interactive mode: User prompted for input via TUI
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Scrape B2B reviews for a product")
    parser.add_argument("--product", type=str, help="Product name to search")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument(
        "--source",
        type=str,
        choices=["g2", "capterra"],
        help="Source platform (g2 or capterra)",
    )
    args = parser.parse_args()

    # Validate that if any CLI arg is provided, all are provided
    cli_mode = args.product or args.start_date or args.end_date or args.source
    if cli_mode and not (
        args.product and args.start_date and args.end_date and args.source
    ):
        print(
            "Error: When using command-line arguments, you must provide --product, --start-date, --end-date, and --source"
        )
        sys.exit(1)

    # Configure profile path
    current_dir = os.getcwd()
    user_data_dir = os.path.join(current_dir, "chrome_profile")

    print(f"Starting browser with profile: {user_data_dir}")

    # Initialize browser with persistent profile
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    driver = uc.Chrome(options=options, headless=False)

    # Get product name from CLI or prompt
    if cli_mode:
        query = args.product
        source = args.source
    else:
        source = questionary.select(
            "Select source platform:", choices=["g2", "capterra"]
        ).ask()
        query = questionary.text(
            "Enter product name to search:",
            validate=lambda text: (
                True if text.strip() else "Product name cannot be empty"
            ),
        ).ask()

    try:
        # Call appropriate search function based on source
        if source == "g2":
            search_result = g2_search(driver, query)
        else:  # capterra
            search_result = capterra_search(driver, query)

        selected_product = None
        normalized_query = " ".join(query.split()).lower()

        # Check for 100% match (excluding case and extra spaces)
        for item in search_result:
            if " ".join(item["name"].split()).lower() == normalized_query:
                selected_product = item
                break

        # Handle no exact match based on mode
        if not selected_product:
            if cli_mode:
                # In CLI mode, error out if no perfect match
                print(f"Error: No perfect match found for '{query}'")
                print(f"Close matches: {[item['name'] for item in search_result]}")
                driver.quit()
                sys.exit(1)
            elif search_result:
                # In interactive mode, show TUI prompt
                choices = [item["name"] for item in search_result]
                choice = questionary.select(
                    f"No exact match for '{query}'. Please select from the results:",
                    choices=choices,
                ).ask()
                selected_product = next(
                    item for item in search_result if item["name"] == choice
                )
            else:
                print(f"Error: No results found for '{query}'")
                driver.quit()
                sys.exit(1)

    except Exception as e:
        print(f"Error during {source.upper()} search: {e}")
        driver.quit()
        sys.exit(1)

    # Get date range from CLI or prompt
    if cli_mode:
        date_range = {"start": args.start_date, "end": args.end_date}
    else:
        start_date = questionary.text(
            "Enter start date (YYYY-MM-DD):",
            validate=lambda text: validate_date_range(f"{text} to 2025-12-31"),
        ).ask()
        end_date = questionary.text(
            "Enter end date (YYYY-MM-DD):",
            validate=lambda text: validate_date_range(f"2020-01-01 to {text}"),
        ).ask()
        date_range = {"start": start_date, "end": end_date}

    print(selected_product)
    print(date_range)

    # Only call scrape for G2 (Capterra scrape not yet implemented)
    if source == "g2":
        reviews = g2_scrape(driver, selected_product["product_name"], date_range)
    else:
        reviews = capterra_scrape(driver, selected_product["review_url"], date_range)

    # Create filename from product name and date range
    safe_product_name = (
        selected_product["product_name"].replace(" ", "_").replace("/", "-")
    )
    filename = f"{source}-{safe_product_name}-{date_range['start']}-to-{date_range['end']}.json"

    # Write reviews to file
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(reviews, f, indent=4, ensure_ascii=False)

    print(f"Reviews saved to {filename}")
    driver.quit()


if __name__ == "__main__":
    main()
