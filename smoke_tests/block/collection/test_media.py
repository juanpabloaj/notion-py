from notion.block.collection.media import CollectionViewPageBlock, CollectionViewBlock
from smoke_tests.conftest import assert_block_attributes, assert_block_is_okay


def test_collection_view_block(notion):
    block = notion.root_page.children.add_new(CollectionViewBlock)
    assert_block_is_okay(**locals(), type="collection_view")


def test_collection_view_page_block(notion):
    block = notion.root_page.children.add_new(CollectionViewPageBlock)
    assert_block_is_okay(**locals(), type="collection_view_page")
    assert_block_attributes(block, icon="✔️", cover="cover")
