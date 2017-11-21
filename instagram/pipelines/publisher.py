# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import logging
import time

from scrapy.exceptions import DropItem

from instagram.items import Publisher

logger = logging.getLogger(__name__)
    

class PublisherPipeline(object):

    def open_spider(self, spider):
        self.db = spider.db
        self.coll_name = spider.settings.get('MONGODB_PUBLISHER_COLL_NAME')
        self.coll = self.db[self.coll_name]
        logger.debug('Switched to collection: %s', self.coll_name)

    def process_item(self, item, spider):
        if not isinstance(item, Publisher):
            return item
        
        ts = int(time.time())
        self.coll.update(
            {"_id": item["_id"]},
            {
                "$setOnInsert": {
                    "_id": item["_id"],
                    "username": item["username"],
                    "first_scraped_ts": ts,
                },
                "$set": {
                    "full_name": item["full_name"],
                    "profile_pic_url": item["profile_pic_url"],
                    "profile_pic_url_hd": item["profile_pic_url_hd"],
                    "followed_by": item["followed_by"],
                    "biography": item["biography"],
                    "external_url": item["external_url"],
                    "published_count": item["published_count"],
                    "update_ts": ts,
                    "begin_ts": ts,
                    "status": -1
                }
            },
            upsert=True
        )
        # raise DropItem('Finished processing publisher item: %s', item["_id"]) 
        return item
