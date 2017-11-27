# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Publisher(scrapy.Item):
    _id = scrapy.Field()
    username = scrapy.Field()
    full_name = scrapy.Field()
    profile_pic_url = scrapy.Field()
    profile_pic_url_hd = scrapy.Field()
    followed_by = scrapy.Field()
    biography = scrapy.Field()
    external_url = scrapy.Field()
    published_count = scrapy.Field()
    downloaded_avatar_info = scrapy.Field()


class HashTag(scrapy.Item):
    name = scrapy.Field()
    published_count = scrapy.Field()
    top_posts = scrapy.Field()


class GraphImage(scrapy.Item):
    _id = scrapy.Field()
    instagram_id = scrapy.Field()
    owner_id = scrapy.Field()
    thumbnail_src = scrapy.Field()
    thumbnail_resources = scrapy.Field()
    display_src = scrapy.Field()
    display_resources = scrapy.Field()
    typename = scrapy.Field()
    is_video = scrapy.Field()
    date = scrapy.Field()
    caption = scrapy.Field()
    hashtags = scrapy.Field()
    children = scrapy.Field()
    download_urls = scrapy.Field()
    downloaded_img_info = scrapy.Field()


class GraphVideo(scrapy.Item):
    _id = scrapy.Field()
    instagram_id = scrapy.Field()
    # display_url = scrapy.Field() # related to GraphImage
    video_url = scrapy.Field()
    owner = scrapy.Field()
