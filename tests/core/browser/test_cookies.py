import logging
from unittest.mock import AsyncMock

import pytest

from oddsharvester.core.browser.cookies import CookieDismisser


class TestCookieDismisser:
    @pytest.fixture
    def dismisser(self):
        return CookieDismisser()

    @pytest.mark.asyncio
    async def test_dismiss_cookie_banner_success(self, dismisser, mock_page):
        """Test successful cookie banner dismissal."""
        # Mock successful banner dismissal
        mock_page.wait_for_selector = AsyncMock()
        mock_page.click = AsyncMock()

        result = await dismisser.dismiss(mock_page)
        assert result is True
        mock_page.wait_for_selector.assert_called_once()
        mock_page.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_dismiss_cookie_banner_custom_selector(self, dismisser, mock_page):
        """Test cookie banner dismissal with custom selector."""
        custom_selector = "#custom-cookie-banner"
        mock_page.wait_for_selector = AsyncMock()
        mock_page.click = AsyncMock()

        result = await dismisser.dismiss(mock_page, selector=custom_selector)
        assert result is True
        mock_page.wait_for_selector.assert_called_with(custom_selector, timeout=10000)

    @pytest.mark.asyncio
    async def test_dismiss_cookie_banner_timeout_error(self, dismisser, mock_page):
        """Test cookie banner dismissal when banner is not found (timeout)."""
        mock_page.wait_for_selector.side_effect = TimeoutError("Timeout")

        result = await dismisser.dismiss(mock_page)
        assert result is False

    @pytest.mark.asyncio
    async def test_dismiss_cookie_banner_click_error(self, dismisser, mock_page):
        """Test cookie banner dismissal when click fails."""
        mock_page.wait_for_selector = AsyncMock()
        mock_page.click.side_effect = Exception("Click failed")

        result = await dismisser.dismiss(mock_page)
        assert result is False

    @pytest.mark.asyncio
    async def test_dismiss_cookie_banner_wait_error(self, dismisser, mock_page):
        """Test cookie banner dismissal when wait_for_selector fails."""
        mock_page.wait_for_selector.side_effect = Exception("Wait failed")

        result = await dismisser.dismiss(mock_page)
        assert result is False

    @pytest.mark.asyncio
    async def test_logging_during_cookie_banner_dismissal(self, dismisser, mock_page, caplog):
        """Test logging during cookie banner dismissal."""
        with caplog.at_level(logging.INFO):
            mock_page.wait_for_selector = AsyncMock()
            mock_page.click = AsyncMock()

            await dismisser.dismiss(mock_page)

            assert "Checking for cookie banner" in caplog.text
            assert "Cookie banner found. Dismissing it." in caplog.text

    @pytest.mark.asyncio
    async def test_full_cookie_banner_flow(self, dismisser, mock_page):
        """Test the complete cookie banner dismissal flow."""
        # Mock successful cookie banner dismissal
        mock_page.wait_for_selector = AsyncMock()
        mock_page.click = AsyncMock()

        result = await dismisser.dismiss(mock_page, timeout=5000)
        assert result is True
        mock_page.wait_for_selector.assert_called_once()
        mock_page.click.assert_called_once()

    # =============================================================================
    # GDPR PREFERENCE CENTER TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_dismiss_gdpr_consent_removed(self, dismisser, mock_page):
        """Preference center present and removed from the DOM."""
        mock_page.evaluate = AsyncMock(return_value=1)

        result = await dismisser.dismiss_gdpr_consent(mock_page)
        assert result is True
        mock_page.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_dismiss_gdpr_consent_absent(self, dismisser, mock_page):
        """Nothing removed when the preference center is not in the DOM."""
        mock_page.evaluate = AsyncMock(return_value=0)

        result = await dismisser.dismiss_gdpr_consent(mock_page)
        assert result is False

    @pytest.mark.asyncio
    async def test_dismiss_gdpr_consent_error(self, dismisser, mock_page):
        """Errors are swallowed and reported as failure."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("boom"))

        result = await dismisser.dismiss_gdpr_consent(mock_page)
        assert result is False

    # =============================================================================
    # BOOKMAKER OVERLAY MODAL TESTS
    # =============================================================================

    @pytest.mark.asyncio
    async def test_dismiss_overlay_modal_clicked(self, dismisser, mock_page):
        """Overlay present and dismissed via the close button."""
        mock_page.wait_for_selector = AsyncMock(return_value=AsyncMock())
        mock_page.evaluate = AsyncMock(return_value="clicked")

        result = await dismisser.dismiss_overlay_modal(mock_page)
        assert result is True
        mock_page.evaluate.assert_called_once()

    @pytest.mark.asyncio
    async def test_dismiss_overlay_modal_removed_fallback(self, dismisser, mock_page):
        """Overlay removed from the DOM when the close button is missing."""
        mock_page.wait_for_selector = AsyncMock(return_value=AsyncMock())
        mock_page.evaluate = AsyncMock(side_effect=["not_found", None])

        result = await dismisser.dismiss_overlay_modal(mock_page)
        assert result is True
        assert mock_page.evaluate.call_count == 2

    @pytest.mark.asyncio
    async def test_dismiss_overlay_modal_absent(self, dismisser, mock_page):
        """No overlay present (selector times out)."""
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError

        mock_page.wait_for_selector = AsyncMock(side_effect=PlaywrightTimeoutError("timeout"))

        result = await dismisser.dismiss_overlay_modal(mock_page)
        assert result is False
