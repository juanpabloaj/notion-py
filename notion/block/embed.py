from notion.block.media import MediaBlock
from notion.maps import (
    field_map,
    prefixed_property_map,
    prefixed_field_map,
    property_map,
)
from notion.utils import get_embed_link, remove_signed_prefix_as_needed


class EmbedBlock(MediaBlock):

    _type = "embed"
    _str_fields = "source"

    # TODO: why this exists? is it the same as `source`?
    display_source = prefixed_field_map("format.display_source")
    source = prefixed_property_map("source")
    height = field_map("format.block_height")
    width = field_map("format.block_width")
    full_width = field_map("format.block_full_width")
    page_width = field_map("format.block_page_width")

    def set_source_url(self, url):
        self.source = remove_signed_prefix_as_needed(url)
        self.display_source = get_embed_link(self.source)


class BookmarkBlock(EmbedBlock):

    _type = "bookmark"

    bookmark_cover = field_map("format.bookmark_cover")
    bookmark_icon = field_map("format.bookmark_icon")
    description = property_map("description")
    link = property_map("link")
    title = property_map("title")

    def set_new_link(self, link: str):
        data = {"blockId": self.id, "url": link}
        self._client.post("setBookmarkMetadata", data)
        self.refresh()


class AbstractBlock(EmbedBlock):

    _type = "abstract"


class FramerBlock(EmbedBlock):

    _type = "framer"


class TweetBlock(EmbedBlock):

    _type = "tweet"


class GistBlock(EmbedBlock):

    _type = "gist"


class DriveBlock(EmbedBlock):

    _type = "drive"


class FigmaBlock(EmbedBlock):

    _type = "figma"


class LoomBlock(EmbedBlock):

    _type = "loom"


class MiroBlock(EmbedBlock):

    _type = "miro"


class TypeformBlock(EmbedBlock):

    _type = "typeform"


class CodepenBlock(EmbedBlock):

    _type = "codepen"


class MapsBlock(EmbedBlock):

    _type = "maps"


class InvisionBlock(EmbedBlock):

    _type = "invision"


class WhimsicalBlock(EmbedBlock):

    _type = "whimsical"
