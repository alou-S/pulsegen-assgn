"""
G2 product search functionality.
"""

from .utils import check_captcha

import json
import time
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


def g2_search(driver, query):
    """
    Search for products on G2.

    Args:
        driver: Selenium WebDriver instance
        query: Product name to search for

    Returns:
        List of dicts with 'name' and 'product_name' keys
    """
    encoded_query = quote_plus(query)
    url = f"https://www.g2.com/search/products?max=5&query={encoded_query}"

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
                (
                    By.CSS_SELECTOR,
                    'a[data-event-options*="item_name"][href*="/reviews"]',
                )
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
    Extract product information from G2 search results HTML.

    Args:
        html_content: Raw HTML string from G2 search page

    Returns:
        List of dicts containing product name and URL slug
    """
    soup = BeautifulSoup(html_content, "html.parser")
    products = []
    seen_names = set()

    # Selector targets links with tracking data containing item names and pointing to reviews
    links = soup.select('a[data-event-options*="item_name"][href*="/reviews"]')

    for link in links:
        try:
            data = json.loads(link["data-event-options"])
            name = data.get("item_name")
            url = link.get("href")

            if url:
                url = urlparse(url).path.split("/")[2]

            if name and name not in seen_names:
                products.append({"name": name, "product_name": url})
                seen_names.add(name)
        except (json.JSONDecodeError, KeyError):
            continue

    return products
