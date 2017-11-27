# -*- coding: utf-8 -*-

logging_config = {
    "version": 1,
    "formatters": {
        "scrapy": {
            "format": "[%(levelname).1s]%(asctime)s [%(name)s]: %(message)s"
        },
        "celery": {
            "format": "[%(levelname).1s]%(asctime)s [%(name)s]: %(message)s"
        },
        "poll_instagram": {
            "format": "[%(levelname).1s]%(asctime)s [%(name)s]: %(message)s"
        },
        "sync_publisher": {
            "format": "[%(levelname).1s]%(asctime)s [%(name)s]: %(message)s"
        },
        "fetch_image": {
            "format": "[%(levelname).1s]%(asctime)s [%(name)s]: %(message)s"
        },
    },
    "handlers": {
        "scrapy": {
            "level": "INFO",
            "filters": None,
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "log/scrapy/instagram.log",
            "backupCount": 15,
            "when": "midnight",
            "formatter": 'scrapy'
        },
        "celery": {
            "level": "INFO",
            "filters": None,
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "log/task/celery.log",
            "backupCount": 15,
            "when": "midnight",
            "formatter": 'celery'
        },
        "poll_instagram": {
            "level": "INFO",
            "filters": None,
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "log/task/poll_instagram.log",
            "backupCount": 15,
            "when": "midnight",
            "formatter": 'poll_instagram'
        },
        "sync_publisher": {
            "level": "INFO",
            "filters": None,
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "log/task/sync_publisher.log",
            "backupCount": 15,
            "when": "midnight",
            "formatter": 'sync_publisher'
        },
        "fetch_image": {
            "level": "INFO",
            "filters": None,
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "log/task/fetch_image.log",
            "backupCount": 15,
            "when": "midnight",
            "formatter": 'fetch_image'
        },
    },
    "loggers": {
        "": {
            "handlers": ["scrapy"],
            "propagate": True,
        },
        "celery": {
            "handlers": ["celery"],
            "propagate": True,
        },
        "poll_instagram": {
            "handlers": ["poll_instagram"],
            "propagate": True,
        },
        "sync_publisher": {
            "handlers": ["sync_publisher"],
            "propagate": True,
        },
        "fetch_image": {
            "handlers": ["fetch_image"],
            "propagate": True,
        },
    }
}