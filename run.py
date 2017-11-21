# -*- coding: utf-8 -*-

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from instagram.spiders.spider_publisher import PublisherSpider


if __name__ == '__main__':
    process = CrawlerProcess(get_project_settings())

    # process.crawl(PublisherSpider, target='the_rui_rae')
    process.crawl(PublisherSpider, target='brunomars')
    process.start()
