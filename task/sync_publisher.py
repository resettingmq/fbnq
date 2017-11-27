# -*- coding: utf-8 -*-

import os
import urllib
import json
from io import TextIOWrapper
import traceback

from celery import Celery
from celery.utils.log import get_task_logger

from pymongo import MongoClient

from utils.logger import set_root_logger

from task import settings

app = Celery('instagram')
app.config_from_object('task.config')

set_root_logger()
logger = get_task_logger('sync_publisher')

mongodb_cli = MongoClient(settings.MONGODB_URI)
mongodb_db = mongodb_cli[settings.MONGODB_DB]
mongodb_coll = mongodb_db[settings.MONGODB_PUBLISHER_COLL_NAME]

@app.task(name='sync_publisher', bind=True)
def sync_publisher(self, username):
    set_root_logger()
    logger.info('Begin sync publisher %s from remote.', username)
    jl_ftp_path = os.path.join(
        settings.FTP_ROOT_URI,
        settings.DUMP_DATA_PATH_ROOT,
        settings.DUMP_DATA_PATH_PUBLISHER,
        '{}.jl'.format(username)
    )
    try:
        with urllib.request.urlopen(jl_ftp_path) as resp:
            publisher_info = json.load(TextIOWrapper(resp, 'utf-8'))
        logger.info('Retrieved publisher info: %s', publisher_info)
    except:
        logger.error(
            'Retrieve publisher %s info data FAILED. EXIT. %s',
            username,
            traceback.format_exc()
        )
        return
    try:
        download_avatar_info = publisher_info['downloaded_avatar_info'][0]
        avatar_updated = download_avatar_info['updated']
        if avatar_updated == True:
            avatar_ftp_path = os.path.join(
                settings.FTP_ROOT_URI,
                settings.IMAGE_PATH_ROOT,
                download_avatar_info['path']
            )
            avatar_local_path = os.path.join(
                settings.BASE_PATH,
                settings.IMAGE_PATH_ROOT,
                download_avatar_info['path']
            )
            urllib.request.urlretrieve(avatar_ftp_path, avatar_local_path)
            logger.info('Saved publisher avatar %s to %s', download_avatar_info['path'], avatar_local_path)
    except:
        logger.error(
            'Retrieve publisher %s avatar FAILED. EXIT. %s',
            username,
            traceback.format_exc()
        )
        return
    try:
        ret = mongodb_coll.update(
            {"_id": publisher_info["_id"]},
            publisher_info,
            upsert=True
        )
        if ret['updatedExisting']:
            logger.info('Updated publisher info to MongoDB: %s', publisher_info['username'])
        else:
            logger.info('Inserted publisher info to MongoDB: %s', publisher_info['username'])
    except:
        logger.error(
                'Save publisher info to MongoDB FAILED. EXIT. %s. Error: %s',
                publisher_info['username'],
                traceback.format_exc()
            )
        return
    logger.info('Finished sync publisher info from remote: %s', username)
    return
