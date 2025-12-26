"""
G2 review scraping functionality.
"""

from bs4 import BeautifulSoup
from .utils import check_captcha
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from time import sleep
import random


def extract_reviews(html_content):
    """Extract reviews from G2 HTML content into structured JSON format."""
    soup = BeautifulSoup(html_content, "html.parser")
    reviews = []

    # Find all review articles
    articles = soup.find_all("article", {"itemprop": "review"})

    for article in articles:
        review_data = {}

        # Extract title
        title_elem = article.find("div", {"itemprop": "name"})
        review_data["title"] = title_elem.get_text(strip=True) if title_elem else None

        # Extract rating
        rating_elem = article.find("meta", {"itemprop": "ratingValue"})
        review_data["rating"] = (
            float(rating_elem.get("content")) if rating_elem else None
        )

        # Extract reviewer name
        name_elem = article.find("meta", {"itemprop": "name"})
        review_data["reviewer_name"] = name_elem.get("content") if name_elem else None

        # Extract reviewer role and business size
        role_divs = article.find_all(
            "div",
            class_="elv-tracking-normal elv-font-figtree elv-text-xs elv-leading-xs elv-font-normal elv-text-subtle",
        )
        if len(role_divs) >= 2:
            review_data["reviewer_role"] = role_divs[0].get_text(strip=True)
            # Business size is usually the last one
            review_data["business_size"] = role_divs[-1].get_text(strip=True)
        else:
            review_data["reviewer_role"] = None
            review_data["business_size"] = None

        # Extract date
        date_elem = article.find("meta", {"itemprop": "datePublished"})
        review_data["date"] = date_elem.get("content") if date_elem else None

        # Extract review content by sections
        review_body = article.find("div", {"itemprop": "reviewBody"})
        review_data["review"] = {}

        # Collect all sections from visible review body
        if review_body:
            sections = review_body.find_all("section")
            for section in sections:
                question_elem = section.find(
                    "div",
                    class_="elv-tracking-normal elv-text-default elv-font-figtree elv-text-base elv-leading-base elv-font-bold",
                )
                answer_elem = section.find(
                    "p",
                    class_="elv-tracking-normal elv-text-default elv-font-figtree elv-text-base elv-leading-base",
                )

                if question_elem and answer_elem:
                    question = question_elem.get_text(strip=True)
                    answer = answer_elem.get_text(strip=True)
                    # Remove "Review collected by and hosted on G2.com." text
                    answer = answer.replace(
                        "Review collected by and hosted on G2.com.", ""
                    ).strip()
                    review_data["review"][question] = answer

        # Extract hidden content from "Show More" accordion
        accordion_panel = article.find(
            "div", {"data-elv--accordion--show-more-controller-target": "panel"}
        )
        if accordion_panel:
            hidden_sections = accordion_panel.find_all("section")
            for section in hidden_sections:
                question_elem = section.find(
                    "div",
                    class_="elv-tracking-normal elv-text-default elv-font-figtree elv-text-base elv-leading-base elv-font-bold",
                )
                answer_elem = section.find(
                    "p",
                    class_="elv-tracking-normal elv-text-default elv-font-figtree elv-text-base elv-leading-base",
                )

                if question_elem and answer_elem:
                    question = question_elem.get_text(strip=True)
                    answer = answer_elem.get_text(strip=True)
                    # Remove "Review collected by and hosted on G2.com." text
                    answer = answer.replace(
                        "Review collected by and hosted on G2.com.", ""
                    ).strip()
                    review_data["review"][question] = answer

        reviews.append(review_data)

    return reviews


def parse_date(date_string):
    """Parse G2 date format to datetime object."""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d")
    except:
        return None


def get_page_reviews(driver, product, page_num):
    """Fetch and extract reviews from a specific page."""
    print(f"Fetching page {page_num} for product {product}")
    url = f"https://www.g2.com/products/{product}/reviews?filters%5Bcomment_answer_values%5D=&order=most_recent&page={page_num}#reviews"
    driver.get(url)
    check_captcha(driver)

    # Check for 500 error page
    html_content = driver.page_source
    if '<h1 class="error-text-number">500</h1>' in html_content:
        print(f"Page {page_num} returned 500 error - no more reviews")
        return []

    wait = WebDriverWait(driver, 10)
    try:
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'article[itemprop="review"]')
            )
        )
    except:
        return []

    html_content = driver.page_source
    return extract_reviews(html_content)


def filter_reviews_by_date(reviews, start_date, end_date):
    """Filter reviews to only include those within date range."""
    filtered = []
    for review in reviews:
        if review.get("date"):
            review_date = parse_date(review["date"])
            if review_date and start_date <= review_date <= end_date:
                filtered.append(review)
    return filtered


def find_page_range(driver, product, start_date, end_date, max_page=1000):
    """
    Use optimized binary search to find the page range containing reviews within date range.
    Returns: (first_page, last_page, all_reviews_in_range)

    Since reviews are ordered most_recent, earlier pages have newer dates.
    Optimization: Seed search based on date distribution from first page to avoid unnecessary searches.
    """
    start_date = parse_date(start_date) if isinstance(start_date, str) else start_date
    end_date = parse_date(end_date) if isinstance(end_date, str) else end_date

    # Cache to avoid re-fetching pages
    page_cache = {}
    all_reviews = []

    def get_cached_page(page):
        if page not in page_cache:
            page_cache[page] = get_page_reviews(driver, product, page)
            sleep(random.randint(300, 500) / 100)
        return page_cache[page]

    def get_page_date_range(page):
        """Get the earliest and latest dates on a page."""
        reviews = get_cached_page(page)
        if not reviews:
            return None, None

        dates = [parse_date(r["date"]) for r in reviews if r.get("date")]
        dates = [d for d in dates if d]

        if not dates:
            return None, None
        return min(dates), max(dates)

    # OPTIMIZATION: Fetch first page to analyze date distribution
    print("Analyzing first page to optimize search...")
    page_1_reviews = get_cached_page(1)

    if not page_1_reviews:
        print("No reviews found on first page")
        return None, None, []

    # Get date range from first page
    page_1_dates = [parse_date(r["date"]) for r in page_1_reviews if r.get("date")]
    page_1_dates = [d for d in page_1_dates if d]

    if not page_1_dates:
        print("No valid dates on first page")
        return None, None, []

    newest_date = max(page_1_dates)
    oldest_date_page_1 = min(page_1_dates)
    reviews_per_page = len(page_1_reviews)

    # Calculate days per page to estimate search range
    if newest_date != oldest_date_page_1:
        days_per_page = (
            (newest_date - oldest_date_page_1).days
            / reviews_per_page
            * reviews_per_page
        )
    else:
        days_per_page = 1  # Conservative estimate if all same date

    # Estimate max page based on date range needed
    if days_per_page > 0:
        days_to_target = (newest_date - start_date).days
        estimated_max_page = max(
            10, int(days_to_target / days_per_page * 1.5)
        )  # 1.5x buffer
        max_page = min(max_page, estimated_max_page)
    else:
        max_page = 100  # Fallback

    # If target end_date is newer than newest review, no results possible
    if end_date < oldest_date_page_1:
        print("Target date range ends before oldest review on page 1")
        return None, None, []

    # If target start_date is newer than newest review, no results possible
    if start_date > newest_date:
        print("Target date range starts after newest review")
        return None, None, []

    # OPTIMIZATION: Use exponential search first for quick convergence
    # Instead of binary search from 1 to max_page, do exponential jumps

    # If page 1 has reviews in range, start there
    earliest_p1, latest_p1 = oldest_date_page_1, newest_date
    if start_date <= latest_p1 and earliest_p1 <= end_date:
        first_page = 1
    else:
        # Use smarter initial search based on estimated position
        if days_per_page > 0:
            estimated_start_page = max(
                1, int((newest_date - end_date).days / days_per_page)
            )
            probe_page = max(2, estimated_start_page)
        else:
            probe_page = 2

        # Exponential search to find rough bounds
        first_page = None
        step = 1
        while probe_page <= max_page:
            earliest, latest = get_page_date_range(probe_page)

            if earliest is None:
                break

            # Check if this page overlaps with target date range
            if start_date <= latest and earliest <= end_date:
                # Found a page in range, narrow down with binary search
                left = max(1, probe_page // 2) if probe_page > 1 else 1
                right = probe_page

                while left <= right:
                    mid = (left + right) // 2
                    earliest, latest = get_page_date_range(mid)

                    if earliest is None:
                        right = mid - 1
                        continue

                    if latest < start_date:
                        right = mid - 1
                    elif earliest > end_date:
                        left = mid + 1
                    else:
                        first_page = mid
                        right = mid - 1
                break
            elif latest < start_date:
                # Gone too far, target is earlier
                break

            # Keep searching forward
            probe_page += step
            step *= 2

    if first_page is None:
        print("No reviews found in target date range")
        return None, None, []

    print(f"First page with target reviews: {first_page}")

    # Find last page with reviews in range using similar optimization
    # Estimate where last page might be based on date range
    if days_per_page > 0:
        days_span = (end_date - start_date).days
        estimated_page_span = max(
            1, int(days_span / days_per_page * 1.2)
        )  # 1.2x buffer
        estimated_last_page = min(max_page, first_page + estimated_page_span)
    else:
        estimated_last_page = min(max_page, first_page + 10)

    print(f"Searching for last page between {first_page} and {estimated_last_page}...")

    last_page = first_page
    left, right = first_page, estimated_last_page

    while left <= right:
        mid = (left + right) // 2
        earliest, latest = get_page_date_range(mid)

        if earliest is None:  # No more reviews
            right = mid - 1
            continue

        if earliest > end_date:
            # All reviews too new, search earlier pages
            right = mid - 1
        elif latest < start_date:
            # All reviews too old, search later pages
            left = mid + 1
        else:
            # This page has reviews in range
            last_page = mid
            left = mid + 1  # Try to find later page

    # Collect all reviews from cached pages within range
    for page in range(first_page, last_page + 1):
        if page in page_cache:
            page_reviews = page_cache[page]
        else:
            page_reviews = get_page_reviews(driver, product, page)

        filtered = filter_reviews_by_date(page_reviews, start_date, end_date)
        all_reviews.extend(filtered)

    return first_page, last_page, all_reviews


def g2_scrape(driver, selected_product, date_range):
    """
    Scrape G2 reviews for a product within a date range.

    Args:
        driver: Selenium WebDriver instance
        selected_product: Product slug from G2 URL
        date_range: Dict with 'start' and 'end' date strings (YYYY-MM-DD)

    Returns:
        List of review dictionaries
    """
    start_date = date_range.get("start") or date_range.get("from")
    end_date = date_range.get("end") or date_range.get("to")

    if not start_date or not end_date:
        print(f"Invalid date range format: {date_range}")
        return []

    first_page, last_page, reviews = find_page_range(
        driver, selected_product, start_date, end_date
    )

    if first_page is None:
        print(f"No reviews found in date range {start_date} to {end_date}")
        return []

    print(f"Found reviews in pages {first_page} to {last_page}")
    print(f"Total reviews in range: {len(reviews)}")

    return reviews
