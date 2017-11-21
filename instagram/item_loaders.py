from scrapy.loader import ItemLoader
from scrapy.loader.processors import TakeFirst, Identity, Compose

from . import items


class PublisherLoader(ItemLoader):
    default_item_class = items.Publisher
    default_output_processor = TakeFirst()


class HashTagLoader(ItemLoader):
    default_item_class = items.HashTag
    default_output_processor = TakeFirst()

    top_posts_out = Identity()


class GraphImageLoader(ItemLoader):
    default_item_class = items.GraphImage
    default_output_processor = TakeFirst()

    thumbnail_resources_out = Identity()
    display_resources_out = Identity()
    hashtags_out = Identity()
    children_out = Identity()
    # download_urls_out = Compose(dict)
    downloaded_img_info_out = Identity()
