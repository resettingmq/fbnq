# -*- coding: utf-8 -*-

from scrapy.pipelines.images import ImagesPipeline
from scrapy import Request

from instagram.items import Publisher


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
