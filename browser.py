"""
OAK BUILDERS LLC - Bid Finder
Shared Playwright Browser Manager

Provides a headless Chromium browser for scraping JavaScript-rendered pages.
Falls back gracefully when Playwright is not installed (e.g., Render free tier).

Usage:
    from browser import browser_fetch, is_browser_available

    if is_browser_available():
        html = browser_fetch("https://example.com/bids")
        soup = BeautifulSoup(html, "lxml")
"""

import atexit

_playwright_instance = None
_browser = None


def is_browser_available() -> bool:
    """Check if Playwright + Chromium are installed."""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


def _get_browser():
    """Get or create the shared browser instance (lazy init)."""
    global _playwright_instance, _browser

    if _browser is not None:
        try:
            # Check if browser is still connected
            _browser.contexts
            return _browser
        except Exception:
            _browser = None
            _playwright_instance = None

    from playwright.sync_api import sync_playwright

    _playwright_instance = sync_playwright().start()
    _browser = _playwright_instance.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",  # Avoid /dev/shm issues in Docker
            "--disable-gpu",
            "--disable-extensions",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--no-first-run",
        ],
    )
    atexit.register(cleanup)
    return _browser


def browser_fetch(
    url: str,
    wait_for: str = None,
    timeout: int = 20000,
    wait_until: str = "domcontentloaded",
) -> str:
    """
    Fetch a URL with headless Chromium and return the fully rendered HTML.

    Args:
        url: The URL to fetch.
        wait_for: Optional CSS selector to wait for before capturing HTML.
        timeout: Navigation timeout in milliseconds.
        wait_until: Playwright load state - "domcontentloaded", "load", or "networkidle".

    Returns:
        The fully rendered HTML content of the page.
    """
    browser = _get_browser()
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )
    page = context.new_page()

    try:
        page.goto(url, timeout=timeout, wait_until=wait_until)

        # Wait for dynamic content to load
        if wait_for:
            try:
                page.wait_for_selector(wait_for, timeout=8000)
            except Exception:
                pass  # Selector not found, continue with whatever loaded

        # Give React/Angular apps a moment to render
        page.wait_for_timeout(1500)

        return page.content()
    finally:
        context.close()


def browser_fetch_with_login(
    login_url: str,
    target_url: str,
    email: str,
    password: str,
    email_selector: str = 'input[type="email"], input[name="email"], input[name="username"]',
    password_selector: str = 'input[type="password"]',
    submit_selector: str = 'button[type="submit"], input[type="submit"]',
    wait_for: str = None,
    timeout: int = 25000,
) -> str:
    """
    Login to a site and then fetch a target page. Returns rendered HTML.

    Args:
        login_url: The login page URL.
        target_url: The page to fetch after login.
        email: Login email/username.
        password: Login password.
        email_selector: CSS selector for email/username input.
        password_selector: CSS selector for password input.
        submit_selector: CSS selector for submit button.
        wait_for: Optional CSS selector to wait for on target page.
        timeout: Navigation timeout in milliseconds.

    Returns:
        The fully rendered HTML of the target page after authentication.
    """
    browser = _get_browser()
    context = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
        locale="en-US",
    )
    page = context.new_page()

    try:
        # Step 1: Navigate to login page
        page.goto(login_url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Step 2: Fill in credentials
        email_input = page.query_selector(email_selector)
        if email_input:
            email_input.fill(email)
        else:
            raise ValueError(f"Email input not found: {email_selector}")

        pw_input = page.query_selector(password_selector)
        if pw_input:
            pw_input.fill(password)
        else:
            raise ValueError(f"Password input not found: {password_selector}")

        # Step 3: Submit
        submit_btn = page.query_selector(submit_selector)
        if submit_btn:
            submit_btn.click()
        else:
            # Try pressing Enter as fallback
            pw_input.press("Enter")

        # Step 4: Wait for navigation after login
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        page.wait_for_timeout(2000)

        # Step 5: Navigate to target page
        page.goto(target_url, timeout=timeout, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        if wait_for:
            try:
                page.wait_for_selector(wait_for, timeout=8000)
            except Exception:
                pass

        return page.content()
    finally:
        context.close()


def cleanup():
    """Clean up browser and Playwright instances."""
    global _browser, _playwright_instance
    try:
        if _browser:
            _browser.close()
    except Exception:
        pass
    try:
        if _playwright_instance:
            _playwright_instance.stop()
    except Exception:
        pass
    _browser = None
    _playwright_instance = None
