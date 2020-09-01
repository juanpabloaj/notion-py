from notion.block.basic import Block
from notion.maps import property_map


class MediaBlock(Block):
    """
    Media block.
    """

    _type = "media"
    _str_fields = "caption"

    caption = property_map("caption")


class BreadcrumbBlock(MediaBlock):
    """
    Breadcrumb block.
    """

    _type = "breadcrumb"
