# -*- coding: utf-8 -*-
from packaging.version import Version
import scrapy
from scrapy.crawler import Crawler
from scrapy.core.scraper import Scraper

from scrapy_rss.items import RssItem, FeedItem, RssedItem
from tests import predefined_items

if Version(scrapy.__version__) < Version('2.13'):
    spider_settings = {}
    if Version(scrapy.__version__) >= Version('2.7') and Version(scrapy.__version__) < Version('2.12'):
        spider_settings['REQUEST_FINGERPRINTER_IMPLEMENTATION'] = '2.7'

    class TestSyncScraper:
        class MySpider(scrapy.Spider):
            custom_settings = spider_settings
            name = 'spider'

        def test_spider_output_handling(self):
            spider = self.MySpider()
            crawler = Crawler(self.MySpider)
            try:
                crawler._apply_settings()
            except AttributeError:
                pass
            scraper = Scraper(crawler)
            scraper.open_spider(spider)
            scraper.crawler.spider = spider

            NSItem0 = predefined_items.NSItem0
            NSItem1 = predefined_items.NSItem1
            NSItem2 = predefined_items.NSItem2

            dummy_params = (None,) * 3
            scraper._process_spidermw_output(RssItem(), *dummy_params)
            scraper._process_spidermw_output(NSItem0(), *dummy_params)
            scraper._process_spidermw_output(NSItem1(), *dummy_params)
            scraper._process_spidermw_output(NSItem2(), *dummy_params)
            scraper._process_spidermw_output(FeedItem(), *dummy_params)
            scraper._process_spidermw_output(RssedItem(), *dummy_params)
            scraper.close_spider(spider)
