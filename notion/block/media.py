from notion.block.common import Block
from notion.maps import property_map


class MediaBlock(Block):
    _type = "media"
    _str_fields = "caption"

    caption = property_map("caption")


class BreadcrumbBlock(MediaBlock):

    _type = "breadcrumb"
