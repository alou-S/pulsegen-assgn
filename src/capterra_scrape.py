"""
Capterra review scraping functionality.
"""

from bs4 import BeautifulSoup
from .utils import check_captcha
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime


def extract_reviews(html_content):
    """Extract reviews from Capterra HTML content into structured JSON format."""
    soup = BeautifulSoup(html_content, "html.parser")
    reviews = []

    # Find all review cards
    review_cards = soup.find_all("div", class_="review-card")

    for card in review_cards:
        review_data = {}

        # Extract title
        title_elem = card.find("h3", class_="fs-3")
        review_data["title"] = (
            title_elem.get_text(strip=True).strip('"') if title_elem else None
        )

        # Extract rating from star-rating-component
        rating_elem = card.select_one(".star-rating-component span.ms-1")
        if rating_elem:
            try:
                review_data["rating"] = float(rating_elem.get_text(strip=True))
            except ValueError:
                review_data["rating"] = None
        else:
            review_data["rating"] = None

        # Extract reviewer name
        name_elem = card.find("div", class_="fw-600")
        review_data["reviewer_name"] = (
            name_elem.get_text(strip=True) if name_elem else None
        )

        # Extract reviewer details (role, company size, usage duration, source, linkedin verification)
        detail_divs = card.find_all("div", class_="fs-4 text-neutral-90 mb-1")

        review_data["reviewer_role"] = None
        review_data["business_type"] = None
        review_data["business_size"] = None
        review_data["usage_duration"] = None
        review_data["source"] = None
        review_data["is_verified_linkedin"] = False

        for div in detail_divs:
            text = div.get_text(strip=True)

            # Check for Verified LinkedIn User
            if "Verified LinkedIn User" in text:
                review_data["is_verified_linkedin"] = True
                continue

            # Check for Source
            if text.startswith("Source:"):
                review_data["source"] = text.replace("Source:", "").strip()
                continue

            # Check for Employees (business type & size combined)
            if "Employees" in text:
                # Split by comma - format is "Business Type, Size Employees"
                parts = text.rsplit(",", 1)
                if len(parts) == 2:
                    review_data["business_type"] = parts[0].strip()
                    review_data["business_size"] = parts[1].strip()
                else:
                    review_data["business_size"] = text
                continue

            # Check for usage duration
            if "Used the Software for:" in text:
                review_data["usage_duration"] = text.replace(
                    "Used the Software for:", ""
                ).strip()
                continue

            # Otherwise it's likely the role (first non-matched field)
            if text and review_data["reviewer_role"] is None:
                review_data["reviewer_role"] = text

        # Extract date - it's inside the div after h3 title, within the d-lg-flex container
        date_elem = card.select_one("div.d-lg-flex div.fs-5.text-neutral-90")
        if date_elem:
            date_text = date_elem.get_text(strip=True)
            review_data["date"] = date_text
        else:
            review_data["date"] = None

        # Extract main review text (the span directly after the rating section)
        review_text_elem = card.select_one(
            "div.d-lg-flex + div.fs-4.lh-2.text-neutral-99"
        )
        if review_text_elem:
            span = review_text_elem.find("span")
            review_data["review_text"] = (
                span.get_text(strip=True)
                if span
                else review_text_elem.get_text(strip=True)
            )
        else:
            review_data["review_text"] = None

        # Extract Pros - find div with "Pros:" text and get sibling content
        pros_container = card.find("div", class_="my-3 my-lg-4")
        if pros_container:
            pros_header = pros_container.find("div", class_="fw-600")
            if pros_header and "Pros:" in pros_header.get_text():
                pros_content = pros_container.find(
                    "div", class_="fs-4 lh-2 text-neutral-99"
                )
                review_data["pros"] = (
                    pros_content.get_text(strip=True) if pros_content else None
                )
            else:
                review_data["pros"] = None
        else:
            review_data["pros"] = None

        # Extract Cons - find div with "Cons:" text and get sibling content
        cons_container = card.find("div", class_="mb-3 mb-lg-4")
        if cons_container:
            cons_header = cons_container.find("div", class_="fw-600")
            if cons_header and "Cons:" in cons_header.get_text():
                cons_content = cons_container.find(
                    "div", class_="fs-4 lh-2 text-neutral-99"
                )
                review_data["cons"] = (
                    cons_content.get_text(strip=True) if cons_content else None
                )
            else:
                review_data["cons"] = None
        else:
            review_data["cons"] = None

        reviews.append(review_data)

    return reviews


def parse_date(date_string):
    """Parse Capterra date format to datetime object."""
    if not date_string:
        return None
    try:
        # ISO format from date_range: "2024-01-01"
        return datetime.strptime(date_string.strip(), "%Y-%m-%d")
    except:
        pass
    try:
        # Capterra format: "17 February 2025"
        return datetime.strptime(date_string.strip(), "%d %B %Y")
    except:
        pass
    try:
        # Alternate format: "February 17, 2025"
        return datetime.strptime(date_string.strip(), "%B %d, %Y")
    except:
        return None


def get_page_reviews(driver, product_link, page_num):
    """Fetch and extract reviews from a specific page."""
    product_name = product_link.rstrip("/").split("/")[-1].replace("-", " ").title()
    print(f"Fetching page {page_num} for {product_name}")

    url = f"{product_link}?page={page_num}&sort=most_recent"

    driver.get(url)
    check_captcha(driver)

    wait = WebDriverWait(driver, 10)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.review-card")))
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


def capterra_scrape(driver, product_link, date_range, max_empty_pages=8):
    """
    Scrape Capterra reviews for a product within a date range.
    Uses linear search with early termination after consecutive empty pages.

    Args:
        driver: Selenium WebDriver instance
        product_link: Full URL to the product page
        date_range: Dict with 'start'/'from' and 'end'/'to' keys
        max_empty_pages: Stop after this many consecutive pages with no matching reviews

    Returns:
        List of review dictionaries
    """
    start_date = date_range.get("start") or date_range.get("from")
    end_date = date_range.get("end") or date_range.get("to")

    if not start_date or not end_date:
        print(f"Invalid date range format: {date_range}")
        return []

    start_date = parse_date(start_date) if isinstance(start_date, str) else start_date
    end_date = parse_date(end_date) if isinstance(end_date, str) else end_date

    all_reviews = []
    consecutive_empty_pages = 0
    page_num = 1

    print(f"Searching for reviews between {start_date.date()} and {end_date.date()}")

    while consecutive_empty_pages < max_empty_pages:
        page_reviews = get_page_reviews(driver, product_link, page_num)

        # No reviews on page means we've hit the end
        if not page_reviews:
            print(f"Page {page_num}: No reviews found (end of reviews)")
            break

        # Filter reviews by date
        matching_reviews = filter_reviews_by_date(page_reviews, start_date, end_date)

        if matching_reviews:
            print(
                f"Page {page_num}: Found {len(matching_reviews)} matching reviews (of {len(page_reviews)} total)"
            )
            all_reviews.extend(matching_reviews)
            consecutive_empty_pages = 0
        else:
            consecutive_empty_pages += 1

        page_num += 1

    if consecutive_empty_pages >= max_empty_pages:
        print(
            f"Stopped after {max_empty_pages} consecutive pages without matching reviews"
        )

    print(f"Total reviews found in date range: {len(all_reviews)}")

    return all_reviews
