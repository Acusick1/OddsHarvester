"""See module docstring in core/browser/__init__.py."""

import logging

from playwright.async_api import Page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from oddsharvester.core.odds_portal_selectors import OddsPortalSelectors
from oddsharvester.utils.constants import COOKIE_BANNER_TIMEOUT_MS


class CookieDismisser:
    """Dismiss the cookie consent banner if present on the page."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def dismiss(
        self,
        page: Page,
        selector: str | None = None,
        timeout: int = COOKIE_BANNER_TIMEOUT_MS,
    ) -> bool:
        """Dismiss the cookie banner if it appears.

        Returns True if a banner was found and dismissed, False otherwise (banner absent or click failed).
        """
        if selector is None:
            selector = OddsPortalSelectors.COOKIE_BANNER

        try:
            self.logger.info("Checking for cookie banner...")
            await page.wait_for_selector(selector, timeout=timeout)
            self.logger.info("Cookie banner found. Dismissing it.")
            await page.click(selector)
            return True

        except PlaywrightTimeoutError:
            self.logger.info("No cookie banner detected.")
            return False

        except Exception as e:
            self.logger.error(f"Error while dismissing cookie banner: {e}")
            return False

    async def dismiss_gdpr_consent(self, page: Page) -> bool:
        """Remove the OneTrust GDPR preference center from the DOM.

        The preference center is always present in the DOM, even when hidden.
        Its list items contain text like "More", which the market-tab "More"
        dropdown logic can match instead of the real navigation element.
        Unconditionally removing it and its backdrop prevents that.

        Returns True if an element was removed, False otherwise.
        """
        try:
            removed = await page.evaluate(
                """(args) => {
                    let count = 0;
                    for (const sel of args) {
                        const el = document.querySelector(sel);
                        if (el) { el.remove(); count++; }
                    }
                    return count;
                }""",
                [
                    OddsPortalSelectors.GDPR_PREFERENCE_CENTER,
                    OddsPortalSelectors.GDPR_PREFERENCE_CENTER_BACKDROP,
                ],
            )
            if removed > 0:
                self.logger.info("OneTrust preference center removed from DOM.")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error removing OneTrust preference center: {e}")
            return False

    async def dismiss_overlay_modal(self, page: Page, timeout: int = 2000) -> bool:
        """Dismiss the bookmaker promotional overlay if present.

        This modal intercepts all pointer events and causes every subsequent
        click to time out. It reappears on each navigation, so this must be
        called per-page. Clicks the close button via a synthetic event, falling
        back to removing the element from the DOM.

        Returns True if an overlay was found and dismissed, False otherwise.
        """
        selector = OddsPortalSelectors.OVERLAY_MODAL
        close_btn_selector = f"{selector} svg.cursor-pointer"

        try:
            overlay = await page.wait_for_selector(selector, state="visible", timeout=timeout)
            if overlay is None:
                return False

            self.logger.info("Bookmaker overlay modal detected. Dismissing...")

            dismissed = await page.evaluate(
                """(sel) => {
                    const btn = document.querySelector(sel);
                    if (btn) {
                        btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
                        return 'clicked';
                    }
                    return 'not_found';
                }""",
                close_btn_selector,
            )

            if dismissed == "clicked":
                self.logger.info("Overlay dismissed via close button.")
                return True

            await page.evaluate(
                """(sel) => {
                    const el = document.querySelector(sel);
                    if (el) el.remove();
                }""",
                selector,
            )
            self.logger.warning("Overlay removed from DOM (close button not found).")
            return True

        except PlaywrightTimeoutError:
            return False

        except Exception as e:
            self.logger.error(f"Error dismissing overlay modal: {e}")
            return False
