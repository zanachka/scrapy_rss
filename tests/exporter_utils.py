# -*- coding: utf-8 -*-
import os
from datetime import datetime

from scrapy_rss.rss import channel_elements

try:
    from tempfile import TemporaryDirectory
except ImportError:
    from backports.tempfile import TemporaryDirectory
from packaging.version import Version

import scrapy
from scrapy import signals
try:
    from scrapy.item import BaseItem
except ImportError:
    from scrapy.item import Item as BaseItem
from scrapy.utils.misc import load_object
from scrapy.utils.test import get_crawler
from scrapy.pipelines import ItemPipelineManager
from twisted.python.failure import Failure

from scrapy_rss.exceptions import *
from scrapy_rss.exporters import FeedItemExporter
from scrapy_rss.utils import get_tzlocal

from tests.utils import FrozenDict


if Version(scrapy.__version__) >= Version('2.13'):
    from twisted.internet import reactor # not used but it's required


class RaisedItemPipelineManager(ItemPipelineManager):
    # @classmethod
    # def _errback(cls, failure, defer):
    #     defer.addErrback(lambda failure: None)  # workaround for Python 2.*
    #     print(failure.getTraceback())
    #     failure.raiseException()

    def process_item(self, item, spider):

        if hasattr(self, 'crawler'):
            if not self.crawler:
                raise Exception('No crawler in spider:' + str(spider))
            # self.crawler.spider = spider
        d = super(RaisedItemPipelineManager, self).process_item(item, spider)
        # d.addErrback(RaisedItemPipelineManager._errback, d)
        if isinstance(d.result, Failure):
            failure = d.result
            d.addErrback(lambda failure: None)  # workaround for Python 2.*
            print(failure.getTraceback())
            failure.raiseException()
        return d



class CrawlerContext(object):
    default_settings = FrozenDict({'ITEM_PIPELINES': {
                                        'scrapy_rss.pipelines.FeedExportPipeline': 900,
                                   },
                                   'LOG_LEVEL': 'WARNING',
                                   'EXTENSIONS': {
                                       'scrapy.extensions.memusage.MemoryUsage': None,},
                                   })

    def __init__(self, feed_file=None, feed_title=None, feed_link=None, feed_description=None,
                 crawler_settings=None):
        settings = crawler_settings if crawler_settings else dict(self.default_settings)
        if feed_file:
            settings['FEED_FILE'] = feed_file
        if feed_title:
            settings['FEED_TITLE'] = feed_title
        if feed_link:
            settings['FEED_LINK'] = feed_link
        if feed_description:
            settings['FEED_DESCRIPTION'] = feed_description
        self.crawler = get_crawler(settings_dict=settings)
        self.spider = scrapy.Spider.from_crawler(self.crawler, 'example.com')
        if hasattr(self.crawler, 'spider'):
            self.crawler.spider = self.spider
        self.spider.parse = lambda response: ()
        item_processor = settings.get('ITEM_PROCESSOR')
        if not item_processor:
            item_processor = RaisedItemPipelineManager
        elif isinstance(item_processor, six.string_types):
            item_processor = load_object(item_processor)

        self.ipm = item_processor.from_crawler(self.crawler)

    def __enter__(self):
        responses = self.crawler.signals.send_catch_log(signal=signals.spider_opened,
                                                        spider=self.spider)
        for _, failure in responses:
            if failure:
                failure.raiseException()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        responses = self.crawler.signals.send_catch_log(signal=signals.spider_closed,
                                                        spider=self.spider, reason=None)
        for _, failure in responses:
            if failure:
                failure.raiseException()


class FullRssItemExporter(FeedItemExporter):
    def __init__(self, file, channel_title, channel_link, channel_description,
                 language='en-US',
                 copyright='Data',
                 managing_editor='m@dot.com (Manager Name)',
                 webmaster='web@dot.com (Webmaster Name)',
                 pubdate=datetime(2000, 2, 1, 0, 10, 30, tzinfo=get_tzlocal()),
                 last_build_date=datetime(2000, 2, 1, 5, 10, 30, tzinfo=get_tzlocal()),
                 category='some category',
                 generator='tester',
                 docs='http://example.com/rss_docs',
                 cloud=FrozenDict({
                     'domain': 'rpc.sys.com',
                     'port': '80',
                     'path': '/RPC2',
                     'registerProcedure': 'myCloud.rssPleaseNotify',
                     'protocol': 'xml-rpc'
                 }),
                 ttl=60,
                 image=channel_elements.ImageElement(url='http://example.com/img.jpg',
                                                     width=54),
                 rating=4.0,
                 text_input=channel_elements.TextInputElement(title='Input title',
                                                              description='Description of input',
                                                              name='Input name',
                                                              link='http://example.com/cgi.py'),
                 skip_hours=(0, 1, 3, 7, 23),
                 skip_days=14,
                 *args, **kwargs):
        super(FullRssItemExporter, self) \
            .__init__(file, channel_title, channel_link, channel_description,
                      language=language, copyright=copyright, managing_editor=managing_editor,
                      webmaster=webmaster, pubdate=pubdate, last_build_date=last_build_date,
                      category=category, generator=generator,
                      docs=docs, cloud=cloud, ttl=ttl,
                      image=image, rating=rating, text_input=text_input,
                      skip_hours=skip_hours, skip_days=skip_days,
                      *args, **kwargs)


default_feed_settings = FrozenDict({'feed_file': 'feed.rss',
                                    'feed_title': 'Title',
                                    'feed_link': 'http://example.com/feed',
                                    'feed_description': 'Description'})


class FeedSettings(TemporaryDirectory):
    def __enter__(self):
        dirname = super(FeedSettings, self).__enter__()
        feed_settings = dict(default_feed_settings)
        feed_settings['feed_file'] = os.path.join(dirname, feed_settings['feed_file'])
        feed_settings = FrozenDict(feed_settings)
        return feed_settings



