# -*- coding: utf-8 -*-

import logging
import time

from scrapy.pipelines.images import ImagesPipeline
from scrapy.http import Request
from scrapy.utils.request import referer_str
from twisted.internet import defer

from instagram.items import GraphImage

GRAPHSIDECAR_TYPE = 'GraphSidecar'

logger = logging.getLogger(__name__)


class ProxiedImagesPipeline(ImagesPipeline):
    # def open_spider(self, spider):
    #     super().open_spider(spider)
    #     self.db = spider.db
    #     self.coll_name = spider.settings.get('MONGODB_GRAPHIMAGE_COLL_NAME')
    #     self.coll = self.db[self.coll_name]

    def process_item(self, item, spider):
        if not isinstance(item, GraphImage):
            return item
        return super().process_item(item, spider)
        
    def get_media_requests(self, item, info):
        # if not info.spider.settings.get('LATEST_ONLY'):
        #     scraped = self.coll.find_one({"_id": item["_id"]})
        #     if scraped is not None:
        #         logger.info('Node already been downloaded. SKIP DOWNLOADING. %s', item["_id"])
        #         return item
        # NOT NECESSARY
        # scraped = self.coll.find_one({"_id": item["_id"]})
        # if scraped is not None and True:
        #     logger.info('Node already been downloaded. SKIP DOWNLOADING. %s', item["_id"])
        #     return item
        meta = info.spider.settings.get("REQUEST_META")
        target_urls = item.get(self.images_urls_field, {})
        if item.get('typename') != GRAPHSIDECAR_TYPE:
            return [Request(url, meta=meta, flags=[code]) for code, url in target_urls.items()]
        # return [Request(url, meta=meta, flags=[code]) for code, url in target_urls.items()]
        return [Request(url, meta=meta, flags=[code, (code == item['_id'])]) for code, url in target_urls.items()]

    def file_path(self, request, response=None, info=None):
        return 'full/{}.jpg'.format(request.flags[0])

    def media_downloaded(self, response, request, info):
        ret = super().media_downloaded(response, request, info)
        try:
            cover = request.flags[1]
        except:
            return ret
        ret.update(cover=cover)
        return ret
