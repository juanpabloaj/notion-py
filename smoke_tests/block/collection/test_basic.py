from notion.block.collection.basic import (
    CollectionBlock,
    CollectionRowBlock,
    TemplateBlock,
)
from smoke_tests.conftest import assert_block_is_okay


def test_collection_block(notion):
    # block = notion.root_page.children.add_new(CollectionBlock)
    # assert_block_is_okay(**locals(), type="collection")
    # TODO: fix this, should it even work at all?
    pass


def test_collection_row_block(notion):
    block = notion.root_page.children.add_new(CollectionRowBlock)
    assert_block_is_okay(**locals(), type="page")


def test_template_block(notion):
    # block = notion.root_page.children.add_new(TemplateBlock)
    # assert_block_is_okay(**locals(), type="template")
    pass
