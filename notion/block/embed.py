from notion.block.media import MediaBlock
from notion.maps import (
    field_map,
    prefixed_property_map,
    prefixed_field_map,
    property_map,
)
from notion.utils import get_embed_link, remove_signed_prefix_as_needed


class EmbedBlock(MediaBlock):
    """
    Embed Block.
    """

    _type = "embed"
    _str_fields = "source"

    display_source = prefixed_field_map("format.display_source")
    source = prefixed_property_map("source")
    height = field_map("format.block_height")
    width = field_map("format.block_width")
    full_width = field_map("format.block_full_width")
    page_width = field_map("format.block_page_width")

    def set_source_url(self, url: str):
        self.source = remove_signed_prefix_as_needed(url)
        self.display_source = get_embed_link(self.source, self._client)


class BookmarkBlock(EmbedBlock):
    """
    Bookmark Block.
    """

    _type = "bookmark"
    _str_fields = "source", "title"

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
    """
    Abstract Block for abstract.com
    """

    _type = "abstract"


class FramerBlock(EmbedBlock):
    """
    Framer Block for framer.com
    """

    _type = "framer"


class TweetBlock(EmbedBlock):
    """
    Tweet Block for twitter.com
    """

    _type = "tweet"


class GistBlock(EmbedBlock):
    """
    Gist Block for gist.github.com
    """

    _type = "gist"


class DriveBlock(EmbedBlock):
    """
    Drive Block for drive.google.com
    """

    _type = "drive"


class FigmaBlock(EmbedBlock):
    """
    Figma Block for figma.io
    """

    _type = "figma"


class LoomBlock(EmbedBlock):
    """
    Loom Block for loom.com
    """

    _type = "loom"


class MiroBlock(EmbedBlock):
    """
    Miro Block for miro.com
    """

    _type = "miro"


class TypeformBlock(EmbedBlock):
    """
    Typeform Block for typeform.com
    """

    _type = "typeform"


class CodepenBlock(EmbedBlock):
    """
    Codepen Block for codepen.io
    """

    _type = "codepen"


class MapsBlock(EmbedBlock):
    """
    Maps Block for maps.google.com
    """

    _type = "maps"


class InvisionBlock(EmbedBlock):
    """
    Invision Block for invisionapp.com
    """

    _type = "invision"


class WhimsicalBlock(EmbedBlock):
    """
    Whimsical Block for whimsical.com
    """

    _type = "whimsical"
