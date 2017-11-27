# -*- coding: utf-8 -*-

import logging
import urllib.parse

from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request
from scrapy.utils.log import failure_to_exc_info
from scrapy.utils.request import referer_str
from twisted.internet import defer

from instagram.items import Publisher

logger = logging.getLogger(__name__)

REDIS_AVATAR_PUBLISHER_KEY = 'avatar:publisher'


class AvatarDownloaderPipeline(ImagesPipeline):
    def __init__(self, *args, settings=None, **kwargs):
        super().__init__(*args, settings=settings, **kwargs)
        self.images_urls_field = settings.get('AVATAR_URL_FIELD')
        self.images_result_field = settings.get('AVATAR_RESULT_FIELD')
        self.avatar_folder = settings.get('AVATAR_FOLDER')

    def process_item(self, item, spider):
        if not isinstance(item, Publisher):
            return item
        return super().process_item(item, spider)

    def get_media_requests(self, item, info):
        meta = info.spider.settings.get("REQUEST_META")
        avatar_url = item.get(self.images_urls_field)
        if avatar_url is None:
            return []
        return [Request(avatar_url, meta=meta, flags=[item['username']])]

    def file_path(self, request, response=None, info=None):
        return '{}/{}.jpg'.format(self.avatar_folder, request.flags[0])

    def item_completed(self, results, item, info):
        item = super().item_completed(results, item, info)
        return item

    def media_to_download(self, request, info):
        def _onsuccess(result):
            if not result:
                return  # returning None force download

            last_modified = result.get('last_modified', None)
            if not last_modified:
                return  # returning None force download

            # DO NOT CHECK avatar EXPIRATION
            # age_seconds = time.time() - last_modified
            # age_days = age_seconds / 60 / 60 / 24
            # if age_days > self.expires:
            #     return  # returning None force download

            try:
                fn = urllib.parse.urlparse(request.url).path.split('/')[-1]
                r_fn = info.spider.redis.hget(
                    REDIS_AVATAR_PUBLISHER_KEY,
                    request.flags[0]
                )
            except:
                return
            if r_fn is None or fn != r_fn.decode('utf-8'):
                logger.info(
                    'Remote avatar file changed. Updating avatar for %s. %s -> %s',
                    request.flags[0],
                    fn,
                    r_fn if r_fn is None else r_fn.decode('utf-8')
                )
                request.flags.append(fn)
                return
                

            referer = referer_str(request)
            logger.debug(
                'File (uptodate): Downloaded %(medianame)s from %(request)s '
                'referred in <%(referer)s>',
                {'medianame': self.MEDIA_NAME, 'request': request,
                 'referer': referer},
                extra={'spider': info.spider}
            )
            self.inc_stats(info.spider, 'uptodate')

            checksum = result.get('checksum', None)
            return {'url': request.url, 'path': path, 'checksum': checksum, 'updated': False}

        path = self.file_path(request, info=info)
        dfd = defer.maybeDeferred(self.store.stat_file, path, info)
        dfd.addCallbacks(_onsuccess, lambda _: None)
        dfd.addErrback(
            lambda f:
            logger.error(self.__class__.__name__ + '.store.stat_file',
                         exc_info=failure_to_exc_info(f),
                         extra={'spider': info.spider})
        )
        return dfd

    def media_downloaded(self, response, request, info):
        ret = super().media_downloaded(response, request, info)
        ret.update(updated=True)
        info.spider.redis.hset(
            REDIS_AVATAR_PUBLISHER_KEY,
            request.flags[0],
            request.flags[1].encode('utf-8'),
        )
        return ret

