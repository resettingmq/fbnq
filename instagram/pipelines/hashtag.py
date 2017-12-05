# -*- coding: utf-8 -*-

import os
import logging
import traceback
import time

from scrapy.exporters import JsonLinesItemExporter
from scrapy.exceptions import DropItem

from celery import Celery

from redis.exceptions import RedisError

from instagram.items import HashTag

logger = logging.getLogger(__name__)

UPDATE_CHECKING_FIELDS = [
    "published_count",
]

REDIS_HASHTAG_REF_COUNT_KEY = 'hashtag_ref_count'


class HashTagPipeline(object):

    def open_spider(self, spider):
        self.redis = spider.redis
        self.db = spider.db
        self.coll_name = spider.settings.get('MONGODB_HASHTAG_COLL_NAME')
        self.coll = self.db[self.coll_name]
        self.export_filepath = os.path.join(
            spider.settings.get('BASE_PATH'),
            spider.settings.get('DUMP_DATA_PATH_ROOT'),
            spider.settings.get('DUMP_DATA_PATH_HASHTAG'),
        )
        if not os.path.exists(self.export_filepath):
            os.makedirs(self.export_filepath)

        self.task = Celery()
        self.task.config_from_object('task.config')
        # logger.debug('Switched to collection: %s', self.coll_name)

    def process_item(self, item, spider):
        if not isinstance(item, HashTag):
            return item
        ts = int(time.time())
        try:
            # if item.get('published_count') is None:
            #     self.redis.zincrby(REDIS_HASHTAG_REF_COUNT_KEY, item["name"], 1)
            is_updated = self._is_updated(item)
            if not is_updated:
                logger.info('Hashtag %s not updated, skip saving to DB', item["name"])
                logger.info('Hashtag %s not updated. No dumping data or sending task', item["name"])
                return item
            ret = self.coll.update(
                {"name": item["name"]},
                {
                    "$setOnInsert": {
                        "name": item["name"],
                        "first_scraped_ts": ts,
                    },
                    "$set": {
                        "published_count": item.get("published_count", None),
                        "update_ts": ts,
                        "begin_ts": ts,
                        "status": -1
                    },
                    "$addToSet": {
                        "top_posts": {"$each": item.get('top_posts', []) }
                    }
                },
                upsert=True
            )
            if ret['updatedExisting']:
                logger.info('Updated hashtag: %s', item["name"])
            else:
                logger.info('Inserted hashtag: %s', item["name"])
            if item.get('published_count') is None:
                logger.info('Exlored hashtag %s. No dumping data or sending task', item["name"])
                return item
            filename = '{}.jl'.format(item["name"])
            filename = os.path.join(self.export_filepath, filename)
            export_file = open(filename, 'wb')
            exportor = JsonLinesItemExporter(export_file)
            exportor.start_exporting()
            exportor.export_item(item)
            exportor.finish_exporting()
            logger.info('dumped item to file: %s', item["name"])
            self.task.send_task('sync_hashtag', (item["name"], ))
            logger.info('Send task sync_hashtag: %s', item["name"])
        except RedisError:
            logger.error('Send task Failed. Network unreachable')
            raise DropItem('Send sync_hashtag task Faied. DROP ITEM %s' % item["name"])
        except:
            logger.error('DB FAILED: %s', traceback.format_exc())
            raise DropItem('Finished processing hashtag item: %s', item)
        return item

    def _is_updated(self, item):
        name = item["name"]
        hashtag = self.coll.find_one({'name': name})
        if hashtag is None:
            return True
        updated = False
        for k in UPDATE_CHECKING_FIELDS:
            if item.get(k) != hashtag.get(k):
                logger.info(
                    'Changed data for %s: %s | %s -> %s',
                    item['name'],
                    k,
                    hashtag.get(k),
                    item.get(k)
                )
                updated = True
        if updated:
            return True
        return False