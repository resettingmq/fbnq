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
logger = get_task_logger('sync_hashtag')

mongodb_cli = MongoClient(settings.MONGODB_URI)
mongodb_db = mongodb_cli[settings.MONGODB_DB]
mongodb_coll = mongodb_db[settings.MONGODB_HASHTAG_COLL_NAME]

@app.task(name='sync_hashtag', bind=True)
def sync_hashtag(self, name):
    set_root_logger()
    logger.info('Begin sync hashtag %s from remote.', name)
    jl_ftp_path = os.path.join(
        settings.FTP_ROOT_URI,
        settings.DUMP_DATA_PATH_ROOT,
        settings.DUMP_DATA_PATH_HASHTAG,
        '{}.jl'.format(name)
    )
    try:
        with urllib.request.urlopen(jl_ftp_path) as resp:
            hashtag_info = json.load(TextIOWrapper(resp, 'utf-8'))
        logger.info('Retrieved hashtag info: %s', hashtag_info)
    except:
        logger.error(
            'Retrieve hashtag %s info data FAILED. EXIT. %s',
            name,
            traceback.format_exc()
        )
        return
    try:
        ret = mongodb_coll.update(
            {"name": hashtag_info["name"]},
            hashtag_info,
            upsert=True
        )
        if ret['updatedExisting']:
            logger.info('Updated hashtag info to MongoDB: %s', hashtag_info['name'])
        else:
            logger.info('Inserted hashtag info to MongoDB: %s', hashtag_info['name'])
    except:
        logger.error(
                'Save hashtag info to MongoDB FAILED. EXIT. %s. Error: %s',
                hashtag_info['name'],
                traceback.format_exc()
            )
        return
    logger.info('Finished sync hashtag info from remote: %s', name)
    return
