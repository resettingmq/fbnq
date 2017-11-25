# -*- coding: utf-8 -*-

from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from celery.utils.log import get_task_logger

from pymongo import MongoClient
import redis

from scrapy.crawler import CrawlerProcess, CrawlerRunner
from scrapy.utils.project import get_project_settings
from scrapy.utils.log import configure_logging

from twisted.internet import reactor

# from instagram.spiders.spider_publisher import PublisherSpider
from instagram.spiders import spider_cls
from utils.logger import set_root_logger

from task import settings

REDIS_UPDATING_KEY = 'updating:{}'
REDIS_LATEST_UPDATE_KEY = 'latest_update'

app = Celery('instagram')
app.config_from_object('task.config')

set_root_logger()
logger = get_task_logger('poll_instagram')

redis_pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB
)

@app.task(name='poll_instagram', bind=True)
def poll_instagram(self):
    set_root_logger()
    redis_cli = redis.StrictRedis(connection_pool=redis_pool)
    latest_update = redis_cli.zrange(
        REDIS_LATEST_UPDATE_KEY,
        0,
        -1
    )
    target_info = None  
    with redis_cli.pipeline() as pipe:
        for t in latest_update:
            t = t.decode('utf8')
            k = REDIS_UPDATING_KEY.format(t)
            try:
                pipe.watch(k)
                is_updating = redis_cli.get(k)
                if is_updating:
                    logger.info('%s is updating. Checking next.', t)
                    continue
                pipe.multi()
                pipe.set(k, 1)
                pipe.execute()
                logger.info('%s is not updating. Begin polling web for it.', t)
                target_info = t
                break
            except redis.WatchError:
                logger.info('%s is updating(simultaneously). Checking next.', t)
                continue

    if target_info is None:
        logger.info('No target found. EXIT polling.')
        return
    
    target, target_type = target_info.split('.')
    spider = spider_cls.get(target_type)
    if spider is None:
        logger.info('No spider found for %s. EXIT.', target_info)
        return
    
    logger.info('Start crawling %s.', target_info)
    configure_logging(install_root_handler=False)
    
    process = CrawlerProcess(get_project_settings())
    process.crawl(spider, target=target, target_type=target_type, target_info=target_info)
    process.start()
    logger.info('End crawling %s.', target_info)
    # runner = CrawlerRunner(get_project_settings())
    # d = runner.crawl(spider, target=target, target_type=target_type, target_info=target_info)
    # d.addBoth(lambda _: logger.info('End crawling %s.', target_info))
    # logger.info('Start crawling %s.', target_info)
    # if not reactor.running:
    #     logger.info('reactor is not running. Run it.')
        # reactor.run()
    # else:
    #     logger.info('reactor is already running.')
    return

@worker_ready.connect
def init_worker(*args, **kwargs):
    logger.info('Initializing worker.')

@worker_shutdown.connect
def shutdown_worker(*args, **kwargs):
    logger.info('Closing worker.')
    # try:
    #     reactor.stop()
    #     logger.info('Shuted down reactor.')
    # except:
    #     pass
