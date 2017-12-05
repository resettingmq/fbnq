# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

import time
import json
from urllib import parse
import re
import traceback

from scrapy import Request, Spider
from pymongo import MongoClient
import redis

from instagram.item_loaders import HashTagLoader, GraphImageLoader

RE_HASHTAG_CONTENT = re.compile(r'\s*#(\w+?)\b')
GRAPHSIDECAR_TYPE = 'GraphSidecar'
DOWNLOAD_MIN_WIDTH = 320

REDIS_LATEST_UPDATE_KEY = 'latest_update'
REDIS_UPDATING_KEY = 'updating:{}'

class BaseInstagramSpider(Spider):
    name = None
    start_url = 'https://www.instagram.com/{}/'
    redis_key_latest_downloaded_ts = None
    redis_key_earliest_downloaded_ts = None
    redis_key_queryid = None
    mongodb_coll_name = None
    re_query_id = None
    target_type = None

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        settings = crawler.settings
        mongo_cli = MongoClient(settings.get('MONGODB_URI'))
        db = mongo_cli[settings.get('MONGODB_DB')]
        pool = redis.ConnectionPool(
            host=settings.get('REDIS_HOST'),
            port=settings.get('REDIS_PORT'),
            db=settings.get('REDIS_DB')
        )
        meta = settings.get('REQUEST_META')
        spider = super().from_crawler(
            crawler,
            *args,
            mongo_cli=mongo_cli,
            db=db,
            redis=redis.StrictRedis(connection_pool=pool),
            meta=meta,
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
        self.coll = self.db[self.mongodb_coll_name]

        # self.redis.sadd(
        #     REDIS_UPDATING_KEY,
        #     '{}.{}'.format(self.target, self.target_type)
        # )
        self.latest_update_ts = self.redis.zscore(
            REDIS_LATEST_UPDATE_KEY,
            '{}.{}'.format(self.target, self.target_type)
        )
        
        self.latest_downloaded_ts = int(self.redis.hget(
            self.redis_key_latest_downloaded_ts,
            self.target
        ) or 0)
        self.latest_downloaded_ts_new = self.latest_downloaded_ts
        self.first_scraping = False if self.latest_downloaded_ts else True
        self.earliest_downloaded_ts = int(self.redis.hget(
            self.redis_key_earliest_downloaded_ts,
            self.target
        ) or 9999999999)
        self.earliest_downloaded_ts_new = self.earliest_downloaded_ts
        self.logger.info(
            'Retrieved latest node downloaded ts for %s -> %s',
            self.target,
            self.latest_downloaded_ts
        )
        self.logger.info(
            'Retrieved earliest node downloaded ts for %s -> %s',
            self.target,
            self.earliest_downloaded_ts
        )
        self.userid = None
        self.scraped = 0

    def start_requests(self):
        yield Request(url=self.start_url.format(self.target), meta=self.meta)

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
            self._clean(res_json)
        except:
            self.logger.error('Get cleaned data failed. ABORT! Error: %s', traceback.format_exc())
            return

        yield from self._process_index_data()

        try:
            nodes = self.cleaned_data["media"]["nodes"]
            self.has_next_page = self.cleaned_data["media"]["page_info"]["has_next_page"]
            self.end_cursor = self.cleaned_data["media"]["page_info"]["end_cursor"]
        except KeyError:
            nodes = []
            self.as_next_page = True
        to_continue = yield from self._get_graphimage_items(nodes)

        if not self.has_next_page:
            self.logger.info('Reached last page. Stop querying')
            return

        if not to_continue:
            self.logger.info('Newest nodes have been scraped. FINISHING SCRAPING')
            return

        query_id = self.redis.get(self.redis_key_queryid)
        if query_id is None:
            request_js_path = response.xpath("//script[@src]/@src").re(r".+Common.+")[0]
            # request_js_path = parse.urljoin(BASE_URL, request_js_path)
            self.logger.info("request js path: %s", request_js_path)
            yield response.follow(
                url=request_js_path,
                callback=self.parse_query_id,
                meta=self.meta
            )
        else:
            self.query_id = query_id
            self.logger.info("Use cached query_id for requesting publisher: %s", query_id)
            query_path = self._get_query_path()
            self.logger.info("Generate url for next scraping(publisher): %s", query_path)
            yield response.follow(
                query_path,
                callback=self.parse_image_nodes,
                meta=self.meta
            )

    def _clean(self, res_json):
        raise NotImplementedError()

    def _process_index_data(self):
        raise NotImplementedError()

    def parse_query_id(self, response):
        query_id_matched = self.re_query_id.search(response.text)
        if query_id_matched is None:
            self.logger.error('query id not found. ABORT!')
            return
        self.query_id = query_id_matched.group(1)
        self.redis.set(
            self.redis_key_queryid,
            self.query_id,
            self.settings.get('QUERYID_EXPIRES_IN')
        )
        self.logger.info('Retreived query id %s', self.query_id)

        query_path = self._get_query_path()
        self.logger.info(
            "Generate url for next scraping(%s): %s",
            self.target_type,
            query_path
        )

        yield response.follow(
            query_path,
            callback=self.parse_image_nodes,
            meta=self.meta
        )

    def parse_image_nodes(self, response):
        # todo: 增加429处理
        json_data = response.text
        try:
            nodes = self._clean_image_node(json_data)
        except (ValueError, TypeError, KeyError):
            res_json = None
            self.logger.error('Parse image nodes js data faield: %s', json_data)
            self.logger.error('Error: %s', traceback.format_exc())
            self.logger.error('Image nodes page data load failed. ABORT')
            return

        to_continue = yield from self._get_graphimage_items(nodes)

        if not self.has_next_page:
            self.logger.info('Reached last page. Stop querying')
            return

        if self.first_scraping and self.scraped > self.max_on_init:
            self.logger.info('Reached MAX_NODE_INIT. Stop querying.')
            return

        if to_continue:
            query_path = self._get_query_path()
            self.logger.info(
                "Generate url for next scraping(%s): %s",
                self.target_type,
                query_path
            )
            yield response.follow(query_path, callback=self.parse_image_nodes, meta=self.meta)

    def parse_detail_json(self, response):
        pass

    def _clean_image_node(self, res_json):
        raise NotImplementedError()

    def _get_query_path(self):
        variables = self._get_query_variables()
        if hasattr(self, 'end_cursor'):
            variables["after"] = self.end_cursor
        query_dict = {
            "query_id": self.query_id,
            "variables": json.dumps(variables)
        }
        
        query_string = parse.urlencode(query_dict)
        # query_string = json.dumps(query_dict)
        return "{}?{}".format(self.settings['QUERY_PATH'], query_string)

    def _get_query_variables(self):
        raise NotImplementedError()

    def _get_graphimage_items(self, nodes, ignore_ts=False):
        self.logger.info(
            'Scraped %s graph images for %s %s. ignore_ts: %s',
            len(nodes),
            self.target_type,
            self.target,
            ignore_ts
        )
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
                loader.add_value('thumbnail_resources', node.get('thumbnail_resources', []))
                loader.add_value('typename', node.get('__typename'))
                loader.add_value('is_video', node['is_video'])
                loader.add_value(
                    'hashtags',
                    [self.hashtag_name] if hasattr(self, 'hashtag_name') else []
                )
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
                # thumbnail_len = len(node.get('thumbnail_resources', []))
                # if thumbnail_len == 0:
                #     loader.add_value('download_urls', [display_src])
                # elif thumbnail_len > 2:
                #     loader.add_value(
                #         'download_urls',
                #         [node['thumbnail_resources'][2].get("src", display_src)]
                #     )
                # else:
                #     loader.add_value(
                #         'download_urls',
                #         [node['thumbnail_resources'][thumbnail_len-1].get("src", display_src)]
                #     )
                loader.add_value(
                    'download_urls',
                    {code: self._get_download_url(node.get('thumbnail_resources', []))}
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
                            hashtag_loader.add_value('explored', True)
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
                if not ignore_ts and self.settings.get('LATEST_ONLY') and image['date'] <= self.latest_downloaded_ts and\
                        image['date'] >= self.earliest_downloaded_ts:
                    self.logger.info(
                        'Current node already scraped: %s => %s(%s) => %s',
                        self.earliest_downloaded_ts,
                        image['date'],
                        image['_id'],
                        self.latest_downloaded_ts
                    )
                    to_continue = False
                    break
                
                if image.get('typename') == GRAPHSIDECAR_TYPE:
                    yield Request(
                        self.settings.get('DETAIL_PAGE_URL').format(code),
                        callback=self.parse_detail_json,
                        meta=self.meta,
                        flags=[image]
                    )
                else:
                    self.scraped += 1
                    yield image

        return to_continue

    def _get_download_url(self, resources):
        sorted_resources = sorted(resources, key=lambda r: r['config_width'])
        for r in sorted_resources:
            if r['config_width'] >= DOWNLOAD_MIN_WIDTH:
                return r['src']


    def closed(self, reason):
        if self.latest_downloaded_ts_new > self.latest_downloaded_ts:
            self.redis.hset(
                self.redis_key_latest_downloaded_ts,
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
        if self.earliest_downloaded_ts_new < self.earliest_downloaded_ts:
            self.redis.hset(
                self.redis_key_earliest_downloaded_ts,
                self.target,
                self.earliest_downloaded_ts_new
            )
            self.logger.info(
                'Updated earliest node downloaded ts for %s -> %s',
                self.target,
                self.earliest_downloaded_ts_new
            )
        else:
            self.logger.info(
                'Not updated earliest node downloaded ts for %s -> %s',
                self.target,
                self.earliest_downloaded_ts
            )
        self._update_db_status(reason)
        # self.redis.srem(
        #     REDIS_UPDATING_KEY,
        #     '.'.join((self.target, self.target_type))
        # )
        self.redis.delete(REDIS_UPDATING_KEY.format(self.target_info))
        self.logger.info('Marked %s NOT updating.', '.'.join((self.target, self.target_type)))
        self.mongo_cli.close()
        self.logger.info('Scaped %s nodes.', self.scraped)
        self.logger.info('Instagram spider closed. Reason: %s', reason) 

    def _update_db_status(self):
        raise NotImplementedError()


from instagram.spiders.spider_publisher import PublisherSpider
from instagram.spiders.spider_hashtag import HashTagSpider

spider_cls = {
    'publisher': PublisherSpider,
    'hashtag': HashTagSpider
}
