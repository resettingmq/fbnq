# -*- coding: utf-8 -*-

# Scrapy settings for instagram project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOT_NAME = 'instagram'

SPIDER_MODULES = ['instagram.spiders']
NEWSPIDER_MODULE = 'instagram.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'instagram (+http://www.yourdomain.com)'
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
"Chrome/61.0.3163.100 Safari/537.36"

# Obey robots.txt rules
# ROBOTSTXT_OBEY = True
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
DOWNLOAD_DELAY = 4
RANDOMIZE_DOWNLOAD_DELAY = True
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'instagram.middlewares.InstagramSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    'instagram.middlewares.MyCustomDownloaderMiddleware': 543,
#}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    'instagram.pipelines.InstagramPipeline': 300,
#}
ITEM_PIPELINES = {
    'instagram.pipelines.avatar_downloader.AvatarDownloaderPipeline': 200,
    'instagram.pipelines.PublisherPipeline': 201,
    'instagram.pipelines.HashTagPipeline': 210,
    'instagram.pipelines.proxied_image_downloader.ProxiedImagesPipeline': 220,
    'instagram.pipelines.GraphImagePipeline': 221,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# AUTOTHROTTLE_ENABLED = True
# AUTOTHROTTLE_START_DELAY = 5
# AUTOTHROTTLE_MAX_DELAY = 60
# AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# AUTOTHROTTLE_DEBUG = True


# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# MongoDB Settings
MONGODB_URI = 'mongodb://127.0.0.1:27017'
MONGODB_DB = 'instagram'
MONGODB_PUBLISHER_COLL_NAME = 'publisher'
MONGODB_HASHTAG_COLL_NAME = 'hashtag'
MONGODB_GRAPHIMAGE_COLL_NAME = 'graphimage'

# Redis settings
REDIS_HOST = 'ubuntu.vm'
REDIS_PORT = 6379
REDIS_DB = 10

LOG_LEVEL = 'INFO'
LOG_ENABLED = False

# Spider related
QUERYID_EXPIRES_IN = 60 * 60 * 24 * 3
NODES_PER_QUERY = 20
MAX_NODE_PUBLISHER_INIT = 20
MAX_NODE_HASHTAG_INIT = 20
LATEST_ONLY = True
REQUEST_META = {
    "proxy": "http://192.168.64.1:1080"
}

# URLs
HASHTAG_INDEX_BASE_URL = 'https://www.instagram.com/explore/tags/'
QUERY_PATH = '/graphql/query/'
DETAIL_PAGE_URL = 'https://www.instagram.com/p/{}/?__a=1'

# Download settings
IMAGES_URLS_FIELD = 'download_urls'
IMAGES_RESULT_FIELD = 'downloaded_img_info'
IMAGES_STORE = './images'

AVATAR_URL_FIELD = 'profile_pic_url'
AVATAR_RESULT_FIELD = 'downloaded_avatar_info'
AVATAR_FOLDER = 'avatar'

DUMP_DATA_PATH_ROOT = 'dump'
DUMP_DATA_PATH_PUBLISHER = 'publisher'
