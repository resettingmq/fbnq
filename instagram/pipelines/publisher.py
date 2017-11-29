# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import os
import logging
import time
import traceback

from scrapy.exporters import JsonLinesItemExporter
from scrapy.exceptions import DropItem

from celery import Celery

from instagram.items import Publisher

logger = logging.getLogger(__name__)

UPDATE_CHECKING_FIELDS = [
    "full_name",
    "profile_pic_url",
    "profile_pic_url_hd",
    "followed_by",
    "biography",
    "published_count"
]
    

class PublisherPipeline(object):

    def open_spider(self, spider):
        self.db = spider.db
        self.coll_name = spider.settings.get('MONGODB_PUBLISHER_COLL_NAME')
        self.coll = self.db[self.coll_name]
        self.export_filepath = os.path.join(
            spider.settings.get('BASE_PATH'),
            spider.settings.get('DUMP_DATA_PATH_ROOT'),
            spider.settings.get('DUMP_DATA_PATH_PUBLISHER'),
        )
        if not os.path.exists(self.export_filepath):
            os.makedirs(self.export_filepath)

        self.task = Celery()
        self.task.config_from_object('task.config')
        # logger.debug('Switched to collection: %s', self.coll_name)

    def process_item(self, item, spider):
        if not isinstance(item, Publisher):
            return item
        ts = int(time.time())
        try:
            is_updated = self._is_updated(item)
            ret = self.coll.update(
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
                        "downloaded_avatar_info": item.get("downloaded_avatar_info"),
                        "update_ts": ts,
                        "begin_ts": ts,
                        "status": -1
                    }
                },
                upsert=True
            )
            if ret['updatedExisting']:
                logger.info('Updated publisher: %s', item["username"])
            else:
                logger.info('Inserted publisher: %s', item["username"])
            if is_updated:
                logger.info('Publisher %s is updated.', item["username"])
                filename = '{}.jl'.format(item["username"])
                filename = os.path.join(self.export_filepath, filename)
                export_file = open(filename, 'wb')
                exportor = JsonLinesItemExporter(export_file)
                exportor.start_exporting()
                exportor.export_item(item)
                exportor.finish_exporting()
                logger.info('dumped item to file: %s', item["username"])
                self.task.send_task('sync_publisher', (item["username"], ))
                logger.info('Send task sync_publisher: %s', item["username"])
            else:
                logger.info(
                    'Publisher %s is not updated. No dumping data or sending task',
                    item["username"]
                )
        except:
            logger.error('DB FAILED: %s', traceback.format_exc())
            raise DropItem('Save publisher to db FAILED. DROP ITEM %s' % item["_id"])
        else:
            return item

    def _is_updated(self, item):
        id_ = item["_id"]
        publisher = self.coll.find_one({'_id': id_})
        if publisher is None:
            return True
        updated = False
        for k in UPDATE_CHECKING_FIELDS:
            if item.get(k) != publisher.get(k):
                logger.info(
                    'Changed data for %s: %s | %s -> %s',
                    item['username'],
                    k,
                    publisher.get(k),
                    item.get(k)
                )
                updated = True
        if updated:
            return True
        avatar_info = item.get("downloaded_avatar_info")
        if avatar_info is not None and avatar_info[0]['updated']:
            return True
        return False

