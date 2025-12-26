"""
Utility functions for the review scraper.
"""

from datetime import datetime


def check_captcha(driver):
    """
    Detect various types of CAPTCHAs on the current page.

    Args:
        driver: Selenium WebDriver instance

    Returns:
        bool: True if CAPTCHA detected, False otherwise
    """
    html_content = driver.page_source.lower()
    original_html = driver.page_source

    captcha_indicators = {
        "verification_required": (
            'class="captcha__human__title"' in original_html
            and "Verification Required" in original_html
        ),
        "recaptcha": (
            "g-recaptcha" in html_content
            or "recaptcha" in html_content
            or "grecaptcha" in html_content
        ),
        "hcaptcha": ("h-captcha" in html_content or "hcaptcha" in html_content),
        "cloudflare": (
            "cf-turnstile" in html_content
            or "cloudflare" in html_content
            and "challenge" in html_content
            or "just a moment" in html_content
        ),
        "funcaptcha": ("funcaptcha" in html_content or "arkoselabs" in html_content),
        "generic": (
            "captcha" in html_content
            or "i'm not a robot" in html_content
            or "i am not a robot" in html_content
            or "prove you're human" in html_content
            or "are you human" in html_content
            or "bot detection" in html_content
        ),
    }

    detected_types = [name for name, detected in captcha_indicators.items() if detected]

    if detected_types:
        print(
            f"CAPTCHA detected ({', '.join(detected_types)})! Please solve it manually..."
        )
        return True

    return False


def validate_date_range(date_range_str):
    """
    Validate a date range string.

    Args:
        date_range_str: String in format 'YYYY-MM-DD to YYYY-MM-DD'

    Returns:
        True if valid, or error message string if invalid
    """
    try:
        start_str, end_str = date_range_str.split(" to ")
        start_date = datetime.strptime(start_str.strip(), "%Y-%m-%d")
        end_date = datetime.strptime(end_str.strip(), "%Y-%m-%d")
        if start_date > end_date:
            return "Start date cannot be after end date."
        return True
    except ValueError:
        return "Invalid format. Please use 'YYYY-MM-DD to YYYY-MM-DD'."
