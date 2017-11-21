# -*- coding: utf-8 -*-

import time
import json
from urllib import parse
import re
import traceback

from scrapy import Request, Spider
from pymongo import MongoClient
import redis

from instagram.item_loaders import PublisherLoader, HashTagLoader, GraphImageLoader

RE_PUBLISHER_QUERY_ID = re.compile(r'profilePosts.+?queryId:\s*"(\d+)"')
RE_HASHTAG_QUERY_ID = re.compile(r'tagMedia.+?queryId:\s*"(\d+)"')
RE_HASHTAG_CONTENT = re.compile(r'\s*#(\w+?)\b')
REQUEST_META = {
    "proxy": "127.0.0.1:1080"
}


class HashTagSpider(Spider):
    name = 'hashtag'
    start_url = 'https://www.instagram.com/explore/tags/{}/'

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        settings = crawler.settings
        mongo_cli = MongoClient(settings.get('MONGODB_URI'))
        db = mongo_cli[settings.get('MONGODB_DB')]
        coll = db[settings.get('MONGODB_HASHTAG_COLL_NAME')]
        pool = redis.ConnectionPool(
            host=settings.get('REDIS_HOST'),
            port=settings.get('REDIS_PORT'),
            db=settings.get('REDIS_DB')
        )
        spider = super().from_crawler(
            crawler,
            *args,
            mongo_cli=mongo_cli,
            db=db,
            coll=coll,
            redis=redis.StrictRedis(connection_pool=pool),
            **kwargs
        )
        spider.logger.debug(
            'Connected to MongoDB: %s/%s',
            settings.get('MONGODB_URL'),
            settings.get('MONGODB_DB')
        )
        return spider

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.latest_downloaded_ts = int(self.redis.hget(
            'latest_downloaded_ts:hashtag',
            self.target
        ) or 0)
        self.first_scraping = False if self.latest_downloaded_ts else True
        self.logger.info(
            'Retrieved latest node downloaded ts for %s -> %s',
            self.target,
            self.latest_downloaded_ts
        )
        self.scraped = 0

    def start_requests(self):
        # TODO: READ FROM DB ON INITIALIZATION
        
        yield Request(url=self.start_url.format(self.target), meta=REQUEST_META)

    def parse(self, response):
        script_tags = response.xpath("//script[@type='text/javascript']/text()").extract()

        for tag in script_tags:
            if not tag.strip().startswith("window"):
                continue
            # self.logger.info(tag)
            json_data = tag.strip().split("= {")[1][:-1]
            json_data = '{' + json_data

            try:
                res_json = json.loads(json_data)
            except (ValueError, TypeError):
                res_json = None
                self.logger.error('Parse index js data faield: %s', json_data)
                self.logger.error('Error: %s', traceback.format_exc())

        if res_json is None:
            self.logger.error('home page data load failed. ABORT')
            return
        
        try:
            hashtag_info = res_json['entry_data']['TagPage'][0]['tag']
        except:
            self.logger.error('Get hash tag info failed. ABORT! Error: %s', traceback.format_exc())
            return
        loader = HashTagLoader()
        top_posts = []
        try:
            loader.add_value('name', hashtag_info['name'])
            loader.add_value('published_count', hashtag_info['media']['count'])
            try:
                top_posts = hashtag_info['top_posts']['nodes']
            except:
                top_posts = []
                self.logger.info('No top posts data found for %s', self.target)
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

        try:
            nodes = hashtag_info["media"]["nodes"]
            has_next_page = hashtag_info["media"]["page_info"]["has_next_page"]
            self.end_cursor = hashtag_info["media"]["page_info"]["end_cursor"]
        except KeyError:
            nodes = []
            has_next_page = True
        to_continue = yield from self._get_graphimage_items(nodes)

        if not has_next_page:
            self.logger.info('Reached last page. Stop querying')
            return

        if not to_continue:
            self.logger.info('Newest nodes have been scraped. FINISHING SCRAPING')
            return

        query_id = self.redis.get('queryid:hashtag')
        if query_id is None:
            request_js_path = response.xpath("//script[@src]/@src").re(r".+Common.+")[0]
            # request_js_path = parse.urljoin(BASE_URL, request_js_path)
            self.logger.info("request js path: %s", request_js_path)
            yield response.follow(
                url=request_js_path,
                callback=self.parse_query_id,
                meta=REQUEST_META
            )
        else:
            self.query_id = query_id
            self.logger.info("Use cached query_id for requesting publisher: %s", query_id)
            query_path = self._get_query_path()
            self.logger.info("Generate url for next scraping(publisher): %s", query_path)
            yield response.follow(
                query_path,
                callback=self.parse_image_nodes,
                meta=REQUEST_META
            )

    def parse_query_id(self, response):
        query_id_matched = RE_HASHTAG_QUERY_ID.search(response.text)
        if query_id_matched is None:
            self.logger.error('query id not found. ABORT!')
            return
        self.query_id = query_id_matched.group(1)
        self.redis.set(
            'queryid:hashtag',
            self.query_id,
            self.settings.get('QUERYID_EXPIRES_IN')
        )
        self.logger.info('Retreived query id %s', self.query_id)

        query_path = self._get_query_path()
        self.logger.info("Generate url for next scraping(hashtag): %s", query_path)

        yield response.follow(
            query_path,
            callback=self.parse_image_nodes,
            meta=REQUEST_META
        )

    def parse_image_nodes(self, response):
        # todo: 增加429处理
        json_data = response.text
        try:
            res_json = json.loads(json_data)['data']['hashtag']['edge_hashtag_to_media']
            has_next_page = res_json["page_info"]["has_next_page"]
            self.end_cursor = res_json["page_info"]["end_cursor"]
            nodes = [node["node"] for node in res_json["edges"]]
        except (ValueError, TypeError, KeyError):
            res_json = None
            self.logger.error('Parse image nodes js data faield: %s', json_data)
            self.logger.error('Error: %s', traceback.format_exc())
            self.logger.error('Image nodes page data load failed. ABORT')
            return

        to_continue = yield from self._get_graphimage_items(nodes)

        if not has_next_page:
            self.logger.info('Reached last page. Stop querying')
            return

        if self.first_scraping and self.scraped > self.settings.get('MAX_NODE_PUBLISHER_INIT'):
            self.logger.info('Reached MAX_NODE_PUBLISHER_INIT. Stop querying.')
            return

        if to_continue:
            query_path = self._get_query_path()
            self.logger.info("Generate url for next scraping(hashtag): %s", query_path)
            yield response.follow(query_path, callback=self.parse_image_nodes, meta=REQUEST_META)
        else:
            self.logger.info('Newest nodes have been scraped. FINISHING SCRAPING')

    def _get_query_path(self):
        variables = {
            "tag_name": self.hashtag_name,
            "first": self.settings.get('NODES_PER_QUERY')
        }
        if hasattr(self, 'end_cursor'):
            variables["after"] = self.end_cursor
        query_dict = {
            "query_id": self.query_id,
            "variables": json.dumps(variables)
        }
        
        query_string = parse.urlencode(query_dict)
        # query_string = json.dumps(query_dict)
        return "{}?{}".format(self.settings['QUERY_PATH'], query_string)

    def _get_graphimage_items(self, nodes, latest_only=True):
        self.logger.info('Scraped %s graph images for tag %s', len(nodes), self.target)
        latest_only = latest_only and self.settings.get('LATEST_ONLY')
        to_continue = True
        # 依赖于nodes有序
        for node in nodes:
            loader = GraphImageLoader()
            try:
                # node = node["node"]
                try:
                    code = node['code']
                except KeyError:
                    code = node['shortcode']
                loader.add_value('_id', code)
                loader.add_value('instagram_id', node['id'])
                loader.add_value('owner_id', node['owner']["id"])
                loader.add_value('thumbnail_src', node.get('thumbnail_src'))
                loader.add_value('thumbnail_resources', node.get('thumbnail_resources'))
                loader.add_value('is_video', node['is_video'])
                loader.add_value('hashtags', [self.hashtag_name])
                try:
                    date = node['date']
                except KeyError:
                    date = node['taken_at_timestamp']
                loader.add_value('date', date)
                try:
                    display_src = node['display_src']
                except KeyError:
                    display_src = node['display_url']
                loader.add_value('display_src', display_src)
                thumbnail_len = len(node.get('thumbnail_resources', []))
                if thumbnail_len == 0:
                    loader.add_value('download_urls', [display_src])
                elif thumbnail_len > 2:
                    loader.add_value(
                        'download_urls',
                        [node['thumbnail_resources'][2].get("src", display_src)]
                    )
                else:
                    loader.add_value(
                        'download_urls',
                        [node['thumbnail_resources'][thumbnail_len-1].get("src", display_src)]
                    )
                try:
                    try:
                        caption = node['caption']
                    except KeyError:
                        caption =  node['edge_media_to_caption']['edges'][0]['node']['text']
                    finally:
                        loader.add_value('caption', caption)

                        hashtags_matched = RE_HASHTAG_CONTENT.findall(caption)
                        for hashtag in hashtags_matched:
                            hashtag_loader = HashTagLoader()
                            hashtag_loader.add_value('name', hashtag)
                            yield hashtag_loader.load_item()

                        loader.add_value('hashtags', hashtags_matched)
                except:
                    self.logger.info('No caption for node: %s', node['shortcode'])
            except:
                self.logger.error(
                    'Missing profile info. NOT UPDATED! Node: %s, Error: %s',
                    node,
                    traceback.format_exc()
                )
                image = None
            else:
                image = loader.load_item()
                if latest_only and image['date'] <= self.latest_downloaded_ts:
                    self.logger.info(
                        'Current node old then existed node: %s(%s) > %s',
                        image['date'],
                        image['_id'],
                        self.latest_downloaded_ts
                    )
                    to_continue = False
                    break
                    
                self.scraped += 1
                yield image

        return to_continue

    def closed(self, reason):
        if self.latest_downloaded_ts_new > self.latest_downloaded_ts:
            self.redis.hset(
                'latest_downloaded_ts:hashtag',
                self.target,
                self.latest_downloaded_ts_new
            )
            self.logger.info(
                'Updated latest node downloaded ts for %s -> %s',
                self.target,
                self.latest_downloaded_ts_new
            )
        else:
            self.logger.info(
                'Not updated latest node downloaded ts for %s -> %s',
                self.target,
                self.latest_downloaded_ts
            )
        end_ts = int(time.time())
        self.coll.update(
            {"name": self.hashtag_name},
            {
                "$set": {
                    "end_ts": end_ts,
                    "status": 1,
                    "latest_downloaded_ts": self.latest_downloaded_ts_new,
                }
            }
        )
        self.redis.zadd(
            'latest_update',
            end_ts,
            '.'.join((self.hashtag_name, 'hashtag'))
        )
        self.mongo_cli.close()
        self.logger.info('Scaped %s nodes.', self.scraped)
        self.logger.info('Instagram spider closed.')
