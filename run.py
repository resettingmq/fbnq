# -*- coding: utf-8 -*-

import logging

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

from instagram.spiders.spider_publisher import PublisherSpider
from utils.logging import set_root_logger


if __name__ == '__main__':
    configure_logging(install_root_handler=False)
    set_root_logger()
    process = CrawlerProcess(get_project_settings())

    # process.crawl(PublisherSpider, target='the_rui_rae')
    process.crawl(PublisherSpider, target='brunomars')
    process.start()
