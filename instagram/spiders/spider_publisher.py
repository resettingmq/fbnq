# -*- coding: utf-8 -*-

import time
import json
from urllib import parse
import re
import traceback

from scrapy import Request, Spider

from instagram.spiders import BaseInstagramSpider
from instagram.item_loaders import PublisherLoader, GraphImageLoader

RE_PUBLISHER_QUERY_ID = re.compile(r'profilePosts.+?queryId:\s*"(\d+)"')
RE_HASHTAG_QUERY_ID = re.compile(r'tagMedia.+?queryId:\s*"(\d+)"')
RE_HASHTAG_CONTENT = re.compile(r'\s*#(\w+?)\b')


class PublisherSpider(BaseInstagramSpider):
    name = 'publisher'
    start_url = 'https://www.instagram.com/{}/'
    redis_key_latest_downloaded_ts = 'latest_downloaded_ts:publisher'
    redis_key_earliest_downloaded_ts = 'earliest_downloaded_ts:publisher'
    redis_key_queryid = 'queryid:publisher'
    mongodb_coll_name = 'publisher'
    re_query_id = RE_PUBLISHER_QUERY_ID
    target_type = 'publisher'

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        settings = crawler.settings
        max_on_init = settings.get('MAX_NODE_PUBLISHER_INIT')
        return super().from_crawler(
            crawler,
            *args,
            max_on_init=max_on_init,
            **kwargs
        )

    def parse_detail_json(self, response):
        json_data = response.text
        image = response.request.flags[0]
        try:
            res_json = json.loads(json_data)
            try:
                children_data = res_json['graphql']['shortcode_media']['edge_sidecar_to_children']['edges']
            except:
                children_data = []
            try:
                display_resources = res_json['graphql']['shortcode_media']['display_resources']
            except:
                display_resources = []
        except:
            children_data = []
            display_resources = []
        image['children'] = []
        for c in children_data:
            try:
                node = c['node']
                loader = GraphImageLoader()
                loader.add_value('_id', node['shortcode'])
                loader.add_value('instagram_id', node['id'])
                loader.add_value('display_src', node['display_url'])
                loader.add_value('display_resources', node['display_resources'])
                loader.add_value('is_video', node['is_video'])
            except:
                self.logger.info(
                    'Load child info FAILED. %s, Error: %s',
                    node,
                    traceback.format_exc()
                )
            else:
                image['children'].append(dict(loader.load_item()))

        image['display_resources'] = display_resources
        for child in image['children']:
            image['download_urls'].update({child['_id']: self._get_download_url(child['display_resources'])})

        yield image

    def _clean(self, res_json):
        self.cleaned_data = res_json['entry_data']['ProfilePage'][0]['user']

    def _process_index_data(self):
        loader = PublisherLoader()
        try:
            loader.add_value('_id', self.cleaned_data['id'])
            loader.add_value('username', self.cleaned_data['username'])
            loader.add_value('full_name', self.cleaned_data.get('full_name'))
            loader.add_value('profile_pic_url', self.cleaned_data.get('profile_pic_url'))
            loader.add_value('profile_pic_url_hd', self.cleaned_data.get('profile_pic_url_hd'))
            loader.add_value('followed_by', self.cleaned_data['followed_by'].get('count'))
            loader.add_value('biography', self.cleaned_data.get('biography'))
            loader.add_value('external_url', self.cleaned_data.get('external_url'))
            loader.add_value('published_count', self.cleaned_data['media']['count'])
        except:
            self.logger.error(
                'Missing profile info. NOT UPDATED! Error: %s',
                traceback.format_exc()
            )
            loader = None
        else:
            user = loader.load_item()
            self.userid = user.get('_id')
            self.published_count = user.get('published_count')
            yield user

    def _clean_image_node(self, res_json):
        res_json = json.loads(res_json)['data']['user']['edge_owner_to_timeline_media']
        self.has_next_page = res_json["page_info"]["has_next_page"]
        self.end_cursor = res_json["page_info"]["end_cursor"]
        nodes = [node["node"] for node in res_json["edges"]]
        return nodes

    def _get_query_variables(self):
        return {
            "id": self.userid,
            "first": self.settings.get('NODES_PER_QUERY')
        }

    def _update_db_status(self, reason):
        if self.userid is None:
            return

        end_ts = int(time.time()) if reason == 'finished' else self.latest_update_ts
        self.coll.update(
            {"_id": self.userid},
            {
                "$set": {
                    "end_ts": end_ts,
                    "status": 1,
                    "latest_downloaded_ts": self.latest_downloaded_ts_new,
                    "earliest_downloaded_ts": self.earliest_downloaded_ts_new
                }
            }
        )
        self.redis.zadd(
            'latest_update',
            end_ts,
            '.'.join((self.target, 'publisher'))
        )
