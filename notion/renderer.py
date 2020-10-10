from typing import Iterable

import mistletoe
from dominate.tags import *
from dominate.util import raw
from mistletoe import block_token, span_token
from mistletoe.html_renderer import HTMLRenderer as MistletoeHTMLRenderer

from notion.block.basic import Block
from notion.block.collection.basic import CollectionBlock

# This is the minimal css stylesheet to apply to get decent looking output.
# It won't make it look exactly like Notion.so but will have the same structure
from notion.settings import CHART_API_URL, TWITTER_API_URL

HTMLRendererStyles = """
<style>
    html, body {
        padding: 20px;
        margin: 20px auto;
        width: 900px;
        font-size: 16px;
        font-family: 
            "-apple-system",
            "BlinkMacSystemFont",
            "Segoe UI",
            "Helvetica",
            "Apple Color Emoji",
            "Arial",
            "sans-serif",
            "Segoe UI Emoji",
            "Segoe UI Symbol";
    }
    .children-list {
        margin-left: cRems(20px);
    }
    .column-list {
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .callout {
        display: flex;
    }
    .callout > .icon {
        flex: 0 1 40px;
    }
    .callout > .text {
        flex: 1 1 auto;
    }
</style>
"""


class MistletoeHTMLRendererSpanTokens(MistletoeHTMLRenderer):
    """
    Renders Markdown to HTML without any MD block tokens (like blockquote)
    except for the paragraph block token, because you need at least one.
    """

    def __enter__(self):
        ret = super().__enter__()
        for klass_name in block_token.__all__[:-1]:  # All but Paragraph token
            block_token.remove_token(getattr(block_token, klass_name))

        # don't auto-link urls in markdown
        span_token.remove_token(span_token.AutoLink)
        return ret

    def render_paragraph(self, token):
        # Only used for span tokens, so don't render out anything
        return self.render_inner(token)


def md(content: str):
    """
    Render the markdown string to HTML, wrapped with dominate "raw" so Dominate
    renders it straight to HTML.
    """
    # NOTE: [:-1] because it adds a newline for some reason
    # TODO: Follow up on this and make it more robust
    # https://github.com/miyuchina/mistletoe/blob/master/mistletoe/block_token.py#L138-L152
    return raw(mistletoe.markdown(content, MistletoeHTMLRendererSpanTokens)[:-1])


def handles_children_rendering(func):
    setattr(func, "handles_children_rendering", True)
    return func


class BaseHTMLRenderer:
    """
    BaseRenderer for HTML output.

    Uses [Dominate](https://github.com/Knio/dominate) internally for generating HTML output.
    Each token rendering method should create a dominate tag and it automatically
    gets added to the parent context (because of the with statement). If you return
    a given tag, it will be used as the parent container for all rendered children
    """

    def __init__(
        self,
        start_block: Block,
        exclude_ids: list = None,
        render_sub_pages: bool = True,
        render_with_styles: bool = False,
        render_linked_pages: bool = False,
        render_table_pages_after_table: bool = False,
    ):
        """
        Attributes
        ----------
        start_block : Block
            The root block to render from.

        exclude_ids : list of str, optional
            Optional list of Block IDs to skip when rendering.
            Defaults to None.

        render_sub_pages : bool, optional
            Whether to render sub pages.
            Defaults to True.

        render_with_styles : bool, optional
            Whether to include CSS styles inside rendered HTML.
            Defaults to False.

        render_linked_pages : bool, optional
            Whether to render linked pages as well.
            Defaults to False.

        # TODO: what?
        render_table_pages_after_table : bool, optional
            Whether to render linked pages after table.
            Defaults to False.
        """
        self._render_stack = []
        self.start_block = start_block
        self.exclude_ids = exclude_ids or []
        self.render_sub_pages = render_sub_pages
        self.render_with_styles = render_with_styles
        self.render_linked_pages = render_linked_pages
        self.render_table_pages_after_table = render_table_pages_after_table

    def _get_previous_sibling_el(self):
        """
        Gets the previous sibling element in the rendered HTML tree
        """
        if not self._render_stack:
            return None

        parent_el = self._render_stack[-1]

        if not parent_el or not parent_el.children:
            return None

        return parent_el.children[-1]

    def _render_blocks_into(self, blocks: Iterable[Block], container_el=None):
        if container_el is None:
            container_el = div(_class="children-list")

        self._render_stack.append(container_el)

        for block in blocks:
            container_el.add(self.render_block(block))

        self._render_stack.pop()
        return [container_el]

    def render_block(self, block: Block) -> list:
        if block.id in self.exclude_ids:
            return []

        renderer = getattr(self, "render_default", None)
        renderer = getattr(self, f"render_{block._type}", renderer)

        if not renderer:
            raise ValueError(f"No handler for block type '{block._type}'.")

        elements = renderer(block=block)

        # TODO: find a better way of marking that information
        # If the block has no children, or the called function handles
        # the child rendering itself, don't render the children
        class_function = getattr(self.__class__, renderer.__name__)
        renders_children = hasattr(class_function, "handles_children_rendering")

        if not block.children or renders_children:
            return elements

        return elements + self._render_blocks_into(block.children, None)

    # == Conversions for rendering notion-py block types to elements ==
    # Each function should return a list containing dominate tags or a string of HTML
    # Marking a function with handles_children_rendering means it handles rendering
    # it's own `.children` and doesn't need to perform the default rendering

    def render_default(self, block):
        return [p(md(block.title))]

    def render_divider(self, **_):
        return [hr()]

    @handles_children_rendering
    def render_column_list(self, block):
        return self._render_blocks_into(
            block.children, div(style="display: flex;", _class="column-list")
        )

    @handles_children_rendering
    def render_column(self, block):
        return self._render_blocks_into(block.children, div(_class="column"))

    def render_to_do(self, block):
        block_id = f"chk_{block.id}"
        return [
            input_(
                label(_for=block_id),
                type="checkbox",
                id=block_id,
                checked=block.checked,
                title=block.title,
            )
        ]

    def render_code(self, block):
        return [pre(code(block.title))]

    def render_factory(self, **_):
        # TODO: implement this?
        return []

    def render_header(self, block):
        return [h2(md(block.title))]

    def render_sub_header(self, block):
        return [h3(md(block.title))]

    def render_sub_sub_header(self, block):
        return [h4(md(block.title))]

    @handles_children_rendering
    def render_page(self, block):
        inner_blocks = self._render_blocks_into(block.children)

        # If it's a child of a collection (CollectionBlock)
        if isinstance(block.parent, CollectionBlock):
            if not self.render_table_pages_after_table:
                return []

            return [h3(md(block.title))] + inner_blocks

        if block.parent.id != block.get("parent_id"):
            # A link is a PageBlock where the parent id
            # doesn't equal the _actual_ parent id of the block
            if not self.render_linked_pages:
                # Render only the link, none of the content in the link
                return [a(h4(md(block.title)), href=block.url)]

        if not self.render_sub_pages and self._render_stack:
            # non-direct subpage rendering, use a simple header
            return [h4(md(block.title))]

        # render a page normally in it's entirety
        # TODO: This should probably not use a "children-list"
        #       but we need to refactor the _render_stack to make that work
        return [h1(md(block.title))] + inner_blocks

    @handles_children_rendering
    def render_bulleted_list(self, block):
        prev_el = self._get_previous_sibling_el()
        if prev_el and isinstance(prev_el, ul):
            container_el = prev_el
        else:
            container_el = ul()

        container_el.add(li(md(block.title)))
        self._render_blocks_into(block.children, container_el)

        # Only return if it's not in the rendered output yet
        if container_el.parent:
            return []

        return [container_el]

    @handles_children_rendering
    def render_numbered_list(self, block):
        prev_el = self._get_previous_sibling_el()
        if prev_el and isinstance(prev_el, ol):
            container_el = prev_el
        else:
            container_el = ol()

        container_el.add(li(md(block.title)))
        self._render_blocks_into(block.children, container_el)

        # Only return if it's not in the rendered output yet
        if container_el.parent:
            return []

        return [container_el]

    def render_toggle(self, block):
        return [details(summary(md(block.title)))]

    def render_quote(self, block):
        return [blockquote(md(block.title))]

    def render_text(self, block):
        return self.render_default(block)

    def render_equation(self, block):
        return [p(img(src=CHART_API_URL + block.latex))]

    def render_embed(self, block):
        src = block.display_source or block.source
        sandbox = "allow-scripts allow-popups allow-forms allow-same-origin"
        el = iframe(src=src, sandbox=sandbox, frameborder=0, allowfullscreen="")
        return [el]

    def render_file(self, block):
        return self.render_embed(block)

    def render_pdf(self, block):
        return self.render_embed(block)

    def render_video(self, block):
        # TODO: this won't work if there's no file extension
        #       we might have to query and get the MIME type
        src = block.display_source or block.source
        ext = "video/" + src.split(".")[-1]
        return [video(source(src=src, type=ext), controls=True)]

    def render_audio(self, block):
        return [audio(src=block.display_source or block.source, controls=True)]

    def render_image(self, block):
        attrs = {"alt": block.caption} if block.caption else {}
        src = block.display_source or block.source
        return [img(src=src, **attrs)]

    def render_bookmark(self, **_):
        # return bookmark_template.format(link=, title=block.title, description=block.description, icon=block.bookmark_icon, cover=block.bookmark_cover)
        # TODO: It's just a social share card for the website we're bookmarking
        return [a(href="block.link")]

    def render_link_to_collection(self, block):
        return [a(md(block.title), href=block.url)]

    def render_breadcrumb(self, block):
        return [p(md(block.title))]

    def render_collection_view_page(self, block):
        return self.render_link_to_collection(block)

    def render_framer(self, block):
        return self.render_embed(block)

    def render_tweet(self, block):
        url = TWITTER_API_URL + block.source
        return block._client.get(url).json()["html"]

    def render_gist(self, block):
        return self.render_embed(block)

    def render_drive(self, block):
        return self.render_embed(block)

    def render_figma(self, block):
        return self.render_embed(block)

    def render_loom(self, block):
        return self.render_embed(block)

    def render_typeform(self, block):
        return self.render_embed(block)

    def render_codepen(self, block):
        return self.render_embed(block)

    def render_maps(self, block):
        return self.render_embed(block)

    def render_invision(self, block):
        return self.render_embed(block)

    def render_callout(self, block):
        icon = div(block.icon, _class="icon")
        title = div(md(block.title), _class="text")
        return [div(icon + title, _class="callout")]

    def render_collection_view(self, block):
        # TODO: render out the table itself

        # Render out all the embedded PageBlocks
        if not self.render_table_pages_after_table:
            return []

        collection_divs = self._render_blocks_into(block.collection.get_rows())
        return [h2(block.title)] + collection_divs

    def render(
        self, indent: str = "  ", pretty: bool = True, xhtml: bool = False
    ) -> str:
        """
        Renders the HTML, kwargs takes kwargs for render() function
        https://github.com/Knio/dominate#rendering


        Attributes
        ----------
        indent : str, optional
            String used for indenting the rendered text.
            Defaults to str consisting of two spaces.

        pretty : bool, optional
            Whether or not to render the HTML in a human-readable way.
            Defaults to True.

        xhtml : bool, False
            Whether or not to use XHTML instead of HTML.
            Example: <br /> instead of <br>
            Defaults to False.


        Returns
        -------
        str
            Rendered blocks.
        """

        def _render_el(e):
            if isinstance(e, dom_tag):
                return e.render(indent=indent, pretty=pretty, xhtml=xhtml)

            return e

        styles = HTMLRendererStyles if self.render_with_styles else ""
        blocks = self.render_block(self.start_block)
        rendered = "".join(_render_el(e) for e in blocks)

        return styles + rendered
