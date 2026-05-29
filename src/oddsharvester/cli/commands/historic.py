"""CLI command for scraping historical matches."""

import asyncio
import json
import logging
import sys

import click

from oddsharvester.cli.options import common_options
from oddsharvester.cli.validators import validate_max_pages, validate_season
from oddsharvester.core.scraper_app import discover_links, run_scraper
from oddsharvester.storage.storage_manager import store_data
from oddsharvester.utils.sport_market_constants import Sport

logger = logging.getLogger(__name__)


@click.command("historic")
@common_options
@click.option(
    "--season",
    required=True,
    callback=validate_season,
    help="Season to scrape (YYYY, YYYY-YYYY, or 'current').",
)
@click.option(
    "--max-pages",
    type=int,
    callback=validate_max_pages,
    help="Maximum number of pages to scrape.",
)
@click.option(
    "--links-only",
    is_flag=True,
    default=False,
    help="Only discover match links (no odds extraction). Outputs a JSON array.",
)
@click.pass_context
def historic(ctx, **kwargs):
    """Scrape historical odds for a league/season."""
    sport = kwargs["sport"]
    storage = kwargs["storage"]
    storage_format = kwargs["storage_format"]
    bookies_filter = kwargs.get("bookies_filter")
    season = kwargs.get("season")
    links_only = kwargs.get("links_only", False)
    sport_value = sport.value if isinstance(sport, Sport) else sport

    if links_only:
        try:
            links = asyncio.run(
                discover_links(
                    sport=sport_value,
                    leagues=kwargs.get("leagues"),
                    season=season,
                    max_pages=kwargs.get("max_pages"),
                    headless=kwargs.get("headless", False),
                    proxy_url=kwargs.get("proxy_url"),
                    proxy_user=kwargs.get("proxy_user"),
                    proxy_pass=kwargs.get("proxy_pass"),
                    browser_user_agent=kwargs.get("browser_user_agent"),
                    browser_locale_timezone=kwargs.get("browser_locale_timezone"),
                    browser_timezone_id=kwargs.get("browser_timezone_id"),
                    base_url=kwargs.get("base_url"),
                )
            )

            file_path = kwargs.get("file_path")
            if file_path:
                with open(file_path, "w") as f:
                    json.dump(links, f, indent=2)
                click.echo(f"Discovered {len(links)} match links, saved to {file_path}")
            else:
                click.echo(json.dumps(links, indent=2))

        except Exception as e:
            logger.error(f"Error during link discovery: {e}", exc_info=True)
            sys.exit(1)
        return

    try:
        scraped_data = asyncio.run(
            run_scraper(
                command="scrape_historic",
                match_links=kwargs.get("match_links"),
                sport=sport_value,
                date=None,
                leagues=kwargs.get("leagues"),
                season=season,
                markets=kwargs.get("markets"),
                max_pages=kwargs.get("max_pages"),
                proxy_url=kwargs.get("proxy_url"),
                proxy_user=kwargs.get("proxy_user"),
                proxy_pass=kwargs.get("proxy_pass"),
                browser_user_agent=kwargs.get("browser_user_agent"),
                browser_locale_timezone=kwargs.get("browser_locale_timezone"),
                browser_timezone_id=kwargs.get("browser_timezone_id"),
                base_url=kwargs.get("base_url"),
                target_bookmaker=kwargs.get("target_bookmaker"),
                scrape_odds_history=kwargs.get("scrape_odds_history", False),
                headless=kwargs.get("headless", False),
                preview_submarkets_only=kwargs.get("preview_submarkets_only", False),
                bookies_filter=bookies_filter.value if bookies_filter else "all",
                period=kwargs.get("period"),
                request_delay=kwargs.get("request_delay", 1.0),
                concurrency_tasks=kwargs.get("concurrency_tasks", 3),
            )
        )

        if scraped_data and scraped_data.success:
            store_data(
                storage_type=storage.value if storage else "local",
                data=scraped_data.success,
                storage_format=storage_format.value if storage_format else "json",
                file_path=kwargs.get("file_path"),
                append=kwargs.get("append", False),
            )
            click.echo(
                f"Successfully scraped {scraped_data.stats.successful} matches "
                f"({scraped_data.stats.failed} failed, {scraped_data.stats.success_rate:.1f}% success rate)."
            )
            if scraped_data.failed:
                click.echo(f"Failed URLs: {[f.url for f in scraped_data.failed]}", err=True)
        else:
            logger.error("Scraper did not return valid data.")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Error during scraping: {e}", exc_info=True)
        sys.exit(1)
