# -*- coding: utf-8 -*-

import os
import urllib
import json
from io import TextIOWrapper
import traceback

from celery import Celery
from celery.utils.log import get_task_logger

from pymongo import MongoClient
import redis

from utils.logger import set_root_logger

from task import settings

app = Celery('instagram')
app.config_from_object('task.config')

set_root_logger()
logger = get_task_logger('fetch_image')

redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB
)

mongodb_cli = MongoClient(settings.MONGODB_URI)
mongodb_db = mongodb_cli[settings.MONGODB_DB]
mongodb_coll = mongodb_db[settings.MONGODB_GRAPHIMAGE_COLL_NAME]

@app.task(name='fetch_image', bind=True)
def fetch_image(self, img_id):
    set_root_logger()
    logger.info('Begin sync graph image %s from remote.', img_id)
    jl_ftp_path = os.path.join(
        settings.FTP_ROOT_URI,
        settings.DUMP_DATA_PATH_ROOT,
        settings.DUMP_DATA_PATH_GRAPHIMAGE,
        '{}.jl'.format(img_id)
    )
    try:
        with urllib.request.urlopen(jl_ftp_path) as resp:
            img_info = json.load(TextIOWrapper(resp, 'utf-8'))
        logger.info('Retrieved image info: %s', img_info)
    except:
        logger.error(
            'Retrieve image %s info data FAILED. EXIT. %s',
            img_id,
            traceback.format_exc()
        )
        return
    downloaded_img_info = img_info[settings.IMAGES_RESULT_FIELD]
    for img in downloaded_img_info:
        img_ftp_path = os.path.join(
            settings.FTP_ROOT_URI,
            settings.IMAGE_PATH_ROOT,
            img['path']
        )
        img_local_path = os.path.join(
            settings.BASE_PATH,
            settings.IMAGE_PATH_ROOT,
            img['path']
        )
        try:
            urllib.request.urlretrieve(img_ftp_path, img_local_path)
            logger.info('Saved image %s to %s', img, img_local_path)
        except:
            logger.error(
                'Retrieve image %s FAILED. EXIT. %s',
                img,
                traceback.format_exc()
            )
            return
    try:
        ret = mongodb_coll.update(
            {"_id": img_info["_id"]},
            img_info,
            upsert=True
        )
        if ret['updatedExisting']:
            logger.info('Updated graph image info to MongoDB: %s', img_info["_id"])
        else:
            logger.info('Inserted graph image info to MongoDB: %s', img_info["_id"])
    except:
        logger.error(
                'Save graph image info to MongoDB FAILED. EXIT. %s. Error: %s',
                img_info["_id"],
                traceback.format_exc()
            )
        return
    logger.info('Finished sync graph image from remote: %s', img_id)
    return
