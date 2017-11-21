# -*- coding: utf-8 -*-

import logging
import traceback
import time

from scrapy.exceptions import DropItem

from instagram.items import GraphImage

logger = logging.getLogger(__name__)
    

class GraphImagePipeline(object):

    def open_spider(self, spider):
        self.db = spider.db
        self.coll_name = spider.settings.get('MONGODB_GRAPHIMAGE_COLL_NAME')
        self.coll = self.db[self.coll_name]
        self.existed = 0
        self.inserted = 0
        self.latest_downloaded_ts = spider.latest_downloaded_ts
        self.earliest_downloaded_ts = spider.earliest_downloaded_ts
        logger.debug('Switched to collection: %s', self.coll_name)

    def close_spider(self, spider):
        spider.latest_downloaded_ts_new = self.latest_downloaded_ts
        spider.earliest_downloaded_ts_new = self.earliest_downloaded_ts
        logger.info('Existed graph images: %s', self.existed)
        logger.info('Inserted graph images: %s', self.inserted)

    def process_item(self, item, spider):
        if not isinstance(item, GraphImage):
            return item
        try:
            ret = self.coll.update(
                {"_id": item["_id"]},
                {
                    "$setOnInsert": {
                        "_id": item["_id"],
                        "instagram_id": item["instagram_id"],
                        "owner_id": item["owner_id"],
                        "thumbnail_src": item["thumbnail_src"],
                        "thumbnail_resources": item["thumbnail_resources"],
                        "typename": item.get("typename"),
                        "is_video": item["is_video"],
                        "date": item["date"],
                        "display_src": item["display_src"],
                        "caption": item["caption"],
                        "download_urls": item["download_urls"],
                        "downloaded_img_info": item.get("downloaded_img_info"),
                        "status": 1,
                        "scraped_ts": int(time.time()),
                    },
                    "$set": {
                        "update_ts": int(time.time())
                    },
                    "$addToSet": {
                        "hashtags": {"$each": item.get('hashtags', []) }
                    }
                },
                upsert=True
            )
            if item["date"] > self.latest_downloaded_ts:
                self.latest_downloaded_ts = item["date"]
            if item["date"] < self.earliest_downloaded_ts:
                self.earliest_downloaded_ts = item["date"]
            if ret['updatedExisting']:
                logger.info('Updated graph images: %s', item["_id"])
                self.existed += 1
            else:
                logger.info('Inserted graph images: %s', ret['upserted'])
                self.inserted += 1
        except:
            logger.error('DB FAILED: %s', traceback.format_exc())
            raise DropItem('Save graph image to db FAILED. DROP ITEM %s' % item["_id"])
        else:
            return item