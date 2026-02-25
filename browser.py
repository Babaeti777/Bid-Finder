"""
OAK BUILDERS LLC - Bid Finder
Shared Playwright Browser Manager

Provides a headless Chromium browser for scraping JavaScript-rendered pages.
Falls back gracefully when Playwright is not installed.

Key design: All Playwright operations run in a dedicated worker thread
to avoid "Sync API inside asyncio loop" errors in gunicorn/Flask.

Usage:
    from browser import browser_fetch, is_browser_available

    if is_browser_available():
        html = browser_fetch("https://example.com/bids")
        soup = BeautifulSoup(html, "lxml")
"""

import os
import atexit
import threading
from concurrent.futures import Future


def is_browser_available() -> bool:
    """Check if Playwright + Chromium are installed and the binary exists."""
    try:
        from playwright.sync_api import sync_playwright
        # Quick check: can we actually find chromium?
        p = sync_playwright().start()
        try:
            path = p.chromium.executable_path
            exists = os.path.exists(path)
            if not exists:
                print(f"[Browser] Chromium not found at {path}")
            return exists
        except Exception:
            return False
        finally:
            p.stop()
    except ImportError:
        return False
    except Exception as e:
        print(f"[Browser] Availability check failed: {e}")
        return False


# ============================================================
# Worker thread — runs Playwright sync API outside asyncio loop
# ============================================================

class _BrowserWorker:
    """Runs all Playwright operations in a dedicated thread."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._lock = threading.Lock()
        self._thread = None
        self._started = False

    def _ensure_browser(self):
        """Launch browser if not already running (called inside worker thread)."""
        if self._browser is not None:
            return
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--single-process",
            ],
        )

    def run_in_thread(self, fn):
        """Run a function that uses Playwright in the worker thread.
        The function receives (browser,) as argument and should return a value.
        This method blocks until the function completes."""
        result_future = Future()

        def _worker():
            try:
                with self._lock:
                    self._ensure_browser()
                    result = fn(self._browser)
                result_future.set_result(result)
            except Exception as e:
                result_future.set_exception(e)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        t.join(timeout=60)  # Max 60s per operation

        if t.is_alive():
            result_future.set_exception(TimeoutError("Browser operation timed out (60s)"))

        return result_future.result()

    def shutdown(self):
        with self._lock:
            try:
                if self._browser:
                    self._browser.close()
            except Exception:
                pass
            try:
                if self._pw:
                    self._pw.stop()
            except Exception:
                pass
            self._browser = None
            self._pw = None


_worker = _BrowserWorker()
atexit.register(_worker.shutdown)


# ============================================================
# Public API
# ============================================================

def browser_fetch(
    url: str,
    wait_for: str = None,
    timeout: int = 20000,
    wait_until: str = "domcontentloaded",
) -> str:
    """Fetch a URL with headless Chromium. Returns rendered HTML.
    Safe to call from any thread including asyncio contexts."""

    def _do(browser):
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
            if wait_for:
                try:
                    page.wait_for_selector(wait_for, timeout=8000)
                except Exception:
                    pass
            page.wait_for_timeout(1500)
            return page.content()
        finally:
            context.close()

    return _worker.run_in_thread(_do)


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
    """Login to a site and fetch a target page. Returns rendered HTML.
    Safe to call from any thread including asyncio contexts."""

    def _do(browser):
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
            # Login
            page.goto(login_url, timeout=timeout, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

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

            submit_btn = page.query_selector(submit_selector)
            if submit_btn:
                submit_btn.click()
            else:
                pw_input.press("Enter")

            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)

            # Navigate to target
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

    return _worker.run_in_thread(_do)


def cleanup():
    """Clean up browser and Playwright instances."""
    _worker.shutdown()
