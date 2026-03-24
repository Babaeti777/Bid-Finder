"""
OAK BUILDERS LLC - Bid Finder v2
Headless Browser Module (Playwright)

Same as v1 — thread-safe wrapper around Playwright for JS-rendered pages.
"""

import atexit
import logging
import threading
from concurrent.futures import Future
from typing import Optional

logger = logging.getLogger("browser")

_browser = None
_playwright = None
_lock = threading.Lock()
_worker_thread = None


def is_browser_available() -> bool:
    """Check if Playwright + Chromium are installed."""
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


def _ensure_browser():
    """Start browser on first use."""
    global _browser, _playwright
    if _browser is not None:
        return

    from playwright.sync_api import sync_playwright
    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-setuid-sandbox",
        ],
    )
    atexit.register(cleanup)


def _run_in_worker(fn):
    """Run browser operations in a dedicated thread to avoid asyncio conflicts."""
    future = Future()

    def worker():
        try:
            result = fn()
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return future.result(timeout=60)


def browser_fetch(url: str, wait_for: str = None, timeout: int = 20000) -> Optional[str]:
    """Fetch rendered HTML from a URL."""
    if not is_browser_available():
        return None

    def _do_fetch():
        with _lock:
            _ensure_browser()
            context = _browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            page = context.new_page()
            try:
                page.goto(url, timeout=timeout, wait_until="networkidle")
                if wait_for:
                    try:
                        page.wait_for_selector(wait_for, timeout=10000)
                    except Exception:
                        pass  # Best effort
                return page.content()
            finally:
                page.close()
                context.close()

    try:
        return _run_in_worker(_do_fetch)
    except Exception as e:
        logger.warning(f"Browser fetch failed for {url}: {e}")
        return None


def browser_fetch_with_login(
    login_url: str,
    target_url: str,
    email: str,
    password: str,
    email_selector: str = 'input[type="email"], input[name="email"]',
    password_selector: str = 'input[type="password"], input[name="password"]',
    submit_selector: str = 'button[type="submit"], input[type="submit"]',
    wait_for: str = None,
) -> Optional[str]:
    """Login then fetch a page."""
    if not is_browser_available():
        return None

    def _do_login_fetch():
        with _lock:
            _ensure_browser()
            context = _browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            )
            page = context.new_page()
            try:
                # Login
                page.goto(login_url, timeout=20000, wait_until="networkidle")
                page.fill(email_selector, email)
                page.fill(password_selector, password)
                page.click(submit_selector)
                page.wait_for_load_state("networkidle", timeout=15000)

                # Navigate to target
                page.goto(target_url, timeout=20000, wait_until="networkidle")
                if wait_for:
                    try:
                        page.wait_for_selector(wait_for, timeout=10000)
                    except Exception:
                        pass
                return page.content()
            finally:
                page.close()
                context.close()

    try:
        return _run_in_worker(_do_login_fetch)
    except Exception as e:
        logger.warning(f"Browser login+fetch failed: {e}")
        return None


def cleanup():
    """Shut down browser and Playwright."""
    global _browser, _playwright
    try:
        if _browser:
            _browser.close()
            _browser = None
        if _playwright:
            _playwright.stop()
            _playwright = None
    except Exception:
        pass
