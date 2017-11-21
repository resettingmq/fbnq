# -*- coding: utf-8 -*-

import time
import json
from urllib import parse
import re
import traceback

from scrapy import Request, Spider

from instagram.spiders import BaseInstagramSpider
from instagram.item_loaders import HashTagLoader

RE_PUBLISHER_QUERY_ID = re.compile(r'profilePosts.+?queryId:\s*"(\d+)"')
RE_HASHTAG_QUERY_ID = re.compile(r'tagMedia.+?queryId:\s*"(\d+)"')
RE_HASHTAG_CONTENT = re.compile(r'\s*#(\w+?)\b')


class HashTagSpider(BaseInstagramSpider):
    name = 'hashtag'
    start_url = 'https://www.instagram.com/explore/tags/{}/'
    redis_key_latest_downloaded_ts = 'latest_downloaded_ts:hashtag'
    redis_key_earliest_downloaded_ts = 'earliest_downloaded_ts:hashtag'
    redis_key_queryid = 'queryid:hashtag'
    mongodb_coll_name = 'hashtag'
    re_query_id = RE_HASHTAG_QUERY_ID
    target_type = 'hashtag'

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        settings = crawler.settings
        max_on_init = settings.get('MAX_NODE_HASHTAG_INIT')
        return super().from_crawler(
            crawler,
            *args,
            max_on_init=max_on_init,
            **kwargs
        )

    def _clean(self, res_json):
        self.cleaned_data = res_json['entry_data']['TagPage'][0]['tag']

    def _process_index_data(self):
        loader = HashTagLoader()
        try:
            loader.add_value('name', self.cleaned_data['name'])
            loader.add_value('published_count', self.cleaned_data['media']['count'])
            try:
                top_posts = self.cleaned_data['top_posts']['nodes']
            except:
                top_posts = []
                self.logger.error('No top posts data found for %s', self.target)
            loader.add_value('top_posts', top_posts)
        except:
            self.logger.error(
                'Missing hash tag info. NOT UPDATED! Error: %s',
                traceback.format_exc()
            )
            loader = None
        else:
            hashtag = loader.load_item()
            self.hashtag_name = hashtag.get('name')
            self.published_count = hashtag.get('published_count')
            yield hashtag
            yield from self._get_graphimage_items(top_posts, ignore_ts=True)

    def _clean_image_node(self, res_json):
        res_json = json.loads(res_json)['data']['hashtag']['edge_hashtag_to_media']
        self.has_next_page = res_json["page_info"]["has_next_page"]
        self.end_cursor = res_json["page_info"]["end_cursor"]
        nodes = [node["node"] for node in res_json["edges"]]
        return nodes

    def _get_query_variables(self):
        return {
            "tag_name": self.hashtag_name,
            "first": self.settings.get('NODES_PER_QUERY')
        }

    def _update_db_status(self):
        if self.hashtag_name is None:
            return
        self.coll.update(
            {"name": self.hashtag_name},
            {
                "$set": {
                    "end_ts": int(time.time()),
                    "status": 1,
                    "latest_downloaded_ts": self.latest_downloaded_ts_new,
                    "earliest_downloaded_ts": self.earliest_downloaded_ts_new
                }
            }
        )   
        self.redis.zadd(
            'latest_update',
            int(time.time()),
            '.'.join((self.hashtag_name, 'hashtag'))
        )
