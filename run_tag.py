# -*- coding: utf-8 -*-

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from instagram.spiders.spider_hashtag import HashTagSpider


if __name__ == '__main__':
    process = CrawlerProcess(get_project_settings())

    process.crawl(HashTagSpider, target='24kmagicworldtour')
    process.start()
