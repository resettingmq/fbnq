# -*- coding: utf-8 -*-

import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MONGODB_URI = 'mongodb://192.168.64.1:27017'
MONGODB_DB = 'instagram'

REDIS_HOST = 'ubuntu.vm'
REDIS_PORT = 6379
REDIS_DB = 10

FTP_HOST = 'ubuntu16.vm'
FTP_PORT = 22211
FTP_USER = 'xxmeng'
FTP_PASSWD = 'zaq12WSX'
FTP_ROOT_URI = 'ftp://{}:{}@{}:{}'.format(
    FTP_USER,
    FTP_PASSWD,
    FTP_HOST,
    FTP_PORT
)

DUMP_DATA_PATH_ROOT = 'dump'
DUMP_DATA_PATH_PUBLISHER = 'publisher'
DUMP_DATA_PATH_GRAPHIMAGE = 'graphimage'
IMAGE_PATH = 'images/full'
IMAGES_RESULT_FIELD = 'downloaded_img_info'
