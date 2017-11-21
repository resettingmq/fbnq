# -*- coding: utf-8 -*-

import logging
import traceback
import time

from scrapy.exceptions import DropItem

from instagram.items import HashTag

logger = logging.getLogger(__name__)
    

class HashTagPipeline(object):

    def open_spider(self, spider):
        self.db = spider.db
        self.coll_name = spider.settings.get('MONGODB_HASHTAG_COLL_NAME')
        self.coll = self.db[self.coll_name]
        logger.debug('Switched to collection: %s', self.coll_name)

    def process_item(self, item, spider):
        if not isinstance(item, HashTag):
            return item
        
        try:
            ts = int(time.time())
            exists = self.coll.find_one({"name": item["name"]})
            if exists is None:
                item_dict = dict(item)
                item_dict.update(
                    first_scraped_ts=ts,
                    status=-1
                )
                ret = self.coll.insert_one(item_dict)
                logger.info('Inserted hash tag: %s -> %s', item["name"], ret.inserted_id)
            else:
                self.coll.update(
                    {"name": item["name"]},
                    {
                        "$set": {
                            "published_count": item.get("published_count", None),
                            "update_ts": ts,
                            "begin_ts": ts,
                            "status": -1
                            },
                        "$addToSet": {
                            "top_posts": {"$each": item.get('top_posts', []) }
                        }
                    }
                )
                logger.info('Hashtag existed: %s', item["name"])
        except:
            logger.error('DB FAILED: %s', traceback.format_exc())
            raise DropItem('Finished processing hashtag item: %s', item)
        return item
