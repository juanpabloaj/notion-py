from smoke_tests.conftest import assert_block_is_okay, assert_block_attributes
from notion.block.embed import (
    GistBlock,
    FramerBlock,
    FigmaBlock,
    InvisionBlock,
    LoomBlock,
    MapsBlock,
    TweetBlock,
    TypeformBlock,
    BookmarkBlock,
    CodepenBlock,
    DriveBlock,
    EmbedBlock,
)


def test_embed_block(notion):
    block = notion.root_page.children.add_new(EmbedBlock)
    assert_block_is_okay(**locals(), type="embed")

    assert block.source == ""
    assert block.caption == ""

    caption = "block embed caption"
    block.caption = caption
    block.refresh()

    assert block.caption == caption


def test_bookmark_block(notion):
    block = notion.root_page.children.add_new(BookmarkBlock)
    assert_block_is_okay(**locals(), type="bookmark")

    assert block.link == ""
    assert block.title == ""
    assert block.source == ""
    assert block.description == ""
    assert block.bookmark_icon is None
    assert block.bookmark_cover is None

    link = "github.com/arturtamborski/notion-py/"
    block.set_new_link(link)
    block.refresh()

    assert block.link == link
    assert block.title == "arturtamborski/notion-py"
    assert "This is a fork of the" in block.description
    assert "https://" in block.bookmark_icon
    assert "https://" in block.bookmark_cover

    block.set_source_url(link)
    block.refresh()

    assert block.source == link
    assert block.display_source == link


def test_codepen_block(notion):
    block = notion.root_page.children.add_new(CodepenBlock)
    assert_block_is_okay(**locals(), type="codepen")
    source = "https://codepen.io/MrWeb123/pen/QWyeQwp"
    assert_block_attributes(block, source=source, caption="caption")


def test_drive_block(notion):
    block = notion.root_page.children.add_new(DriveBlock)
    assert_block_is_okay(**locals(), type="drive")
    source = "https://drive.google.com/file/"
    source = source + "d/15kESeWR9wCWT7GW9VvChakTGin68iZsw/view"
    assert_block_attributes(block, source=source, caption="drive")


def test_figma_block(notion):
    block = notion.root_page.children.add_new(FigmaBlock)
    assert_block_is_okay(**locals(), type="figma")


def test_framer_block(notion):
    block = notion.root_page.children.add_new(FramerBlock)
    assert_block_is_okay(**locals(), type="framer")


def test_gist_block(notion):
    block = notion.root_page.children.add_new(GistBlock)
    assert_block_is_okay(**locals(), type="gist")
    source = "https://gist.github.com/arturtamborski/"
    source = source + "539a335fcd71f88bb8c05f316f54ba31"
    assert_block_attributes(block, source=source, caption="caption")


def test_invision_block(notion):
    block = notion.root_page.children.add_new(InvisionBlock)
    assert_block_is_okay(**locals(), type="invision")


def test_loom_block(notion):
    block = notion.root_page.children.add_new(LoomBlock)
    assert_block_is_okay(**locals(), type="loom")


def test_maps_block(notion):
    block = notion.root_page.children.add_new(MapsBlock)
    assert_block_is_okay(**locals(), type="maps")
    source = "https://goo.gl/maps/MrLSwJ3YqdkqekuGA"
    assert_block_attributes(block, source=source, caption="caption")


def test_tweet_block(notion):
    block = notion.root_page.children.add_new(TweetBlock)
    assert_block_is_okay(**locals(), type="tweet")
    source = "https://twitter.com/arturtamborski/status/1289293818609704961"
    assert_block_attributes(block, source=source, caption="caption")


def test_typeform_block(notion):
    block = notion.root_page.children.add_new(TypeformBlock)
    assert_block_is_okay(**locals(), type="typeform")
    source = "https://linklocal.typeform.com/to/I3lVBn"
    assert_block_attributes(block, source=source, caption="caption")
