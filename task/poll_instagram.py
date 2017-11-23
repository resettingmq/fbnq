# -*- coding: utf-8 -*-

from celery import Celery
from celery.utils.log import get_task_logger

from pymongo import MongoClient
import redis

import settings

REDIS_UPDATING_KEY = 'updating'
REDIS_LATEST_UPDATE_KEY = 'latest_update'

app = Celery('instagram_poller')
app.config_from_object('task.config')

logger = get_task_logger(__name__)

redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB
)

@app.task(name='poll_publisher')
def poll_publisher():
    redis_cli = redis.StrictRedis(connection_pool=redis_pool)
    latest_update = redis_cli.zrange(
        REDIS_LATEST_UPDATE_KEY,
        0,
        -1
    )
    target = None
    for t in latest_update:
        is_updating = redis_cli.sismember(
            REDIS_UPDATING_KEY,
            t
        )
        if not is_updating:
            logger.info('%s is not updating. Begin polling web for it.')
            target = t
            break
        logger.info('%s is updating. Checking next.')

    if target is None:
        logger.info('No target found. EXIT polling.')
        return

    mongo_cli = MongoClient(settings.MONGODB_URI)
    db = mongo_cli[settings.MONGODB_DB]
    coll = db['publisher']
    return coll.find()
    # return 'Hello, {}'.format(target)
