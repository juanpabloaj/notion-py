from notion.block.media import BreadcrumbBlock
from smoke_tests.conftest import assert_block_is_okay


def test_media_block(notion):
    pass
    # TODO: fix
    # block = notion.root_page.children.add_new(MediaBlock)
    # assert_block_is_okay(**locals(), type='media')


def test_breadcrumb_block(notion):
    block = notion.root_page.children.add_new(BreadcrumbBlock)
    assert_block_is_okay(**locals(), type="breadcrumb")
