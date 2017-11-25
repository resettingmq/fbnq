# -*- coding: utf-8 -*-

import logging
import os

from utils.logging.config import logging_config

def set_root_logger(settings=None):
    if settings is None or not isinstance(settings, dict):
        logging.config.dictConfig(logging_config)
        return
    settings.setdefault('log_dir', 'log/scrapy')
    settings.setdefault('log_filename', 'instagram.log')
    settings.setdefault('log_backup_count', 15)
    settings.setdefault('log_format', '[%(levelname).1s]%(asctime)s [%(name)s]: %(message)s')
    root_logger = logging.getLogger()
    logger_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(
            settings['log_dir'],
            settings['log_filename']
        ),
        when='midnight',
        backupCount=settings['log_backup_count']
    )
    logger_handler.setLevel(logging.INFO)
    logger_formatter = logging.Formatter(settings['log_format'])
    logger_handler.setFormatter(logger_formatter)
    root_logger.addHandler(logger_handler)