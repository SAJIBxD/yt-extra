class M3U8SnifferError(RuntimeError):
    pass


def get_m3u8_url_and_headers(page_url, timeout_ms=20000, headless=True):
    try:
        from playwright.sync_api import (
            sync_playwright,
            TimeoutError as PlaywrightTimeoutError,
        )
    except ImportError as e:
        raise M3U8SnifferError(
            "Playwright is required. Install with:\n"
            "  pipx inject yt-dlp playwright\n"
            "  playwright install chromium"
        ) from e

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        try:
            with page.expect_request(
                lambda req: req.method == "GET" and ".m3u8" in req.url,
                timeout=timeout_ms,
            ) as req_info:
                page.goto(page_url, wait_until="domcontentloaded")

            req = req_info.value
            return req.url, dict(req.headers)

        except PlaywrightTimeoutError:
            raise M3U8SnifferError("No .m3u8 request found")

        finally:
            browser.close()
