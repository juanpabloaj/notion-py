from notion.block.common import Block
from notion.maps import (
    property_map,
    plaintext_property_map,
    field_map,
    prefixed_field_map,
    nested_field_map,
    boolean_property_map,
)


class BasicBlock(Block):

    _type = "block"
    _str_fields = "title"

    title = property_map("title")
    title_plaintext = plaintext_property_map("title")
    color = field_map("format.block_color")


class DividerBlock(Block):

    _type = "divider"


class PageBlock(BasicBlock):

    _type = "page"

    icon = prefixed_field_map("format.page_icon")
    cover = prefixed_field_map("format.page_cover")


class TextBlock(BasicBlock):

    _type = "text"


class CalloutBlock(BasicBlock):

    _type = "callout"

    icon = field_map("format.page_icon")


class CodeBlock(BasicBlock):

    _type = "code"

    language = property_map("language")
    wrap = field_map("format.code_wrap")


class LinkToPageBlock(BasicBlock):

    _type = "link_to_page"


class EquationBlock(BasicBlock):

    _type = "equation"

    latex = nested_field_map("properties.title")


class QuoteBlock(BasicBlock):

    _type = "quote"


class ToDoBlock(BasicBlock):

    _type = "to_do"
    _str_fields = "checked"

    checked = boolean_property_map("checked")


class ToggleBlock(BasicBlock):

    _type = "toggle"


class HeaderBlock(BasicBlock):

    _type = "header"


class SubHeaderBlock(BasicBlock):

    _type = "sub_header"


class SubSubHeaderBlock(BasicBlock):

    _type = "sub_sub_header"


class BulletedListBlock(BasicBlock):

    _type = "bulleted_list"


class NumberedListBlock(BasicBlock):

    _type = "numbered_list"
