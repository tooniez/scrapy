"""
Base class for Scrapy spiders

See documentation in docs/topics/spiders.rst
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, cast

from scrapy import signals
from scrapy.http import Request, Response
from scrapy.utils.trackref import object_ref
from scrapy.utils.url import url_is_from_spider

if TYPE_CHECKING:
    from collections.abc import Iterable

    from twisted.internet.defer import Deferred

    # typing.Self requires Python 3.11
    from typing_extensions import Self

    from scrapy.crawler import Crawler
    from scrapy.http.request import CallbackT
    from scrapy.settings import BaseSettings, _SettingsKeyT
    from scrapy.utils.log import SpiderLoggerAdapter


class Spider(object_ref):
    """Base class for scrapy spiders. All spiders must inherit from this
    class.
    """

    name: str
    custom_settings: dict[_SettingsKeyT, Any] | None = None

    def __init__(self, name: str | None = None, **kwargs: Any):
        if name is not None:
            self.name: str = name
        elif not getattr(self, "name", None):
            raise ValueError(f"{type(self).__name__} must have a name")
        self.__dict__.update(kwargs)
        if not hasattr(self, "start_urls"):
            self.start_urls: list[str] = []

    @property
    def logger(self) -> SpiderLoggerAdapter:
        from scrapy.utils.log import SpiderLoggerAdapter

        logger = logging.getLogger(self.name)
        return SpiderLoggerAdapter(logger, {"spider": self})

    def log(self, message: Any, level: int = logging.DEBUG, **kw: Any) -> None:
        """Log the given message at the given log level

        This helper wraps a log call to the logger within the spider, but you
        can use it directly (e.g. Spider.logger.info('msg')) or use any other
        Python logger too.
        """
        self.logger.log(level, message, **kw)

    @classmethod
    def from_crawler(cls, crawler: Crawler, *args: Any, **kwargs: Any) -> Self:
        spider = cls(*args, **kwargs)
        spider._set_crawler(crawler)
        return spider

    def _set_crawler(self, crawler: Crawler) -> None:
        self.crawler: Crawler = crawler
        self.settings: BaseSettings = crawler.settings
        crawler.signals.connect(self.close, signals.spider_closed)

    def start_requests(self) -> Iterable[Request]:
        if not self.start_urls and hasattr(self, "start_url"):
            raise AttributeError(
                "Crawling could not start: 'start_urls' not found "
                "or empty (but found 'start_url' attribute instead, "
                "did you miss an 's'?)"
            )
        for url in self.start_urls:
            yield Request(url, dont_filter=True)

    def _parse(self, response: Response, **kwargs: Any) -> Any:
        return self.parse(response, **kwargs)

    if TYPE_CHECKING:
        parse: CallbackT
    else:

        def parse(self, response: Response, **kwargs: Any) -> Any:
            raise NotImplementedError(
                f"{self.__class__.__name__}.parse callback is not defined"
            )

    @classmethod
    def update_settings(cls, settings: BaseSettings) -> None:
        settings.setdict(cls.custom_settings or {}, priority="spider")

    @classmethod
    def handles_request(cls, request: Request) -> bool:
        return url_is_from_spider(request.url, cls)

    @staticmethod
    def close(spider: Spider, reason: str) -> Deferred[None] | None:
        closed = getattr(spider, "closed", None)
        if callable(closed):
            return cast("Deferred[None] | None", closed(reason))
        return None

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.name!r} at 0x{id(self):0x}>"


# Top-level imports
from scrapy.spiders.crawl import CrawlSpider, Rule
from scrapy.spiders.feed import CSVFeedSpider, XMLFeedSpider
from scrapy.spiders.sitemap import SitemapSpider

__all__ = [
    "CSVFeedSpider",
    "CrawlSpider",
    "Rule",
    "SitemapSpider",
    "Spider",
    "XMLFeedSpider",
]
