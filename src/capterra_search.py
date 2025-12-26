"""
Capterra product search functionality.
"""

from .utils import check_captcha

import time
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def capterra_search(driver, query):
    """
    Search for products on Capterra.

    Args:
        driver: Selenium WebDriver instance
        query: Product name to search for

    Returns:
        List of dicts with 'name', 'product_name', and 'review_url' keys
    """
    encoded_query = quote_plus(query)
    url = f"https://www.capterra.in/search/product?q={encoded_query}"

    # Open URL in current window
    driver.get(url)

    # Wait for page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    check_captcha(driver)

    # Wait for search results to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'div.search-result-item, a[href*="/software/"]')
            )
        )
    except:
        # No results found or timeout
        pass

    # Small buffer to ensure page is fully settled
    time.sleep(1)

    html_content = driver.page_source
    return extract_products_and_reviews(html_content)


def extract_products_and_reviews(html_content):
    """
    Extract product information from Capterra search results HTML.

    Args:
        html_content: Raw HTML string from Capterra search page

    Returns:
        List of dicts containing product name, slug, and review URL
    """
    soup = BeautifulSoup(html_content, "html.parser")
    products = []
    seen_names = set()

    # Select the main product card links
    links = soup.select('a.entry[data-evcmp="product-card_search"]')

    for link in links:
        # Stop after collecting 5 products
        if len(products) >= 5:
            break

        try:
            # Extract product name from img alt attribute
            img_elem = link.select_one("img.search-results__thumbnail__img")
            if not img_elem:
                continue

            name = img_elem.get("alt", "").strip()
            if not name:
                continue

            # Extract href (review site URL)
            href = link.get("href")
            if not href:
                continue

            # Prepend base URL to href
            full_url = f"https://www.capterra.in{href}"

            # Parse product identifier from URL (e.g., /software/186634/visual-studio-code)
            url_parts = href.split("/")
            if "software" in url_parts:
                idx = url_parts.index("software")
                # Get the product slug (last part after software ID)
                if idx + 2 < len(url_parts):
                    product_name = url_parts[idx + 2]
                elif idx + 1 < len(url_parts):
                    product_name = url_parts[idx + 1]
                else:
                    product_name = href
            else:
                product_name = href

            if name and name not in seen_names:
                products.append(
                    {"name": name, "product_name": product_name, "review_url": full_url}
                )
                seen_names.add(name)
        except (KeyError, IndexError, AttributeError):
            continue

    return products
