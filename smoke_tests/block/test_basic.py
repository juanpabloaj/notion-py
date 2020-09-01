from notion.block.basic import (
    Block,
    BulletedListBlock,
    CalloutBlock,
    CodeBlock,
    DividerBlock,
    EquationBlock,
    HeaderBlock,
    NumberedListBlock,
    PageBlock,
    LinkToPageBlock,
    QuoteBlock,
    SubHeaderBlock,
    SubSubHeaderBlock,
    TextBlock,
    ToDoBlock,
    ToggleBlock,
    ColumnBlock,
    ColumnListBlock,
    FactoryBlock,
)
from notion.block.collection.media import LinkToCollectionBlock
from smoke_tests.conftest import assert_block_is_okay, assert_block_attributes


def test_block(notion):
    # create basic block from existing page
    block = Block(notion.client, notion.root_page.id)
    parent = notion.root_page.parent
    assert_block_is_okay(**locals(), type="page")

    assert len(block.children) == 0
    assert len(block.parent.id) == 36
    assert block.id == notion.root_page.id


def test_bulleted_list_block(notion):
    block = notion.root_page.children.add_new(BulletedListBlock)
    assert_block_is_okay(**locals(), type="bulleted_list")
    assert_block_attributes(block, title="bulleted_list")


def test_callout_block(notion):
    block = notion.root_page.children.add_new(CalloutBlock)
    assert_block_is_okay(**locals(), type="callout")
    assert_block_attributes(block, icon="✔️", color="blue", title="callout")


def test_code_block(notion):
    block = notion.root_page.children.add_new(CodeBlock)
    assert_block_is_okay(**locals(), type="code")
    assert_block_attributes(block, color="blue", language="Erlang", title="code")


def test_column_block(notion):
    block = notion.root_page.children.add_new(ColumnBlock)
    assert_block_is_okay(**locals(), type="column")

    assert block.column_ratio is None
    assert len(block.children) == 0

    block.column_ratio = 1 / 2
    block.refresh()

    assert block.column_ratio == 1 / 2


def test_column_list_block(notion):
    block = notion.root_page.children.add_new(ColumnListBlock)
    assert_block_is_okay(**locals(), type="column_list")

    assert len(block.children) == 0

    block.children.add_new(ColumnBlock)
    block.children.add_new(ColumnBlock)
    block.evenly_space_columns()
    block.refresh()

    assert len(block.children) == 2
    assert block.children[0].column_ratio == 1 / 2


def test_divider_block(notion):
    block = notion.root_page.children.add_new(DividerBlock)
    assert_block_is_okay(**locals(), type="divider")


def test_equation_block(notion):
    block = notion.root_page.children.add_new(EquationBlock)
    assert_block_is_okay(**locals(), type="equation")
    assert_block_attributes(block, title="E=mc^{2}", color="blue")


def test_factory_block(notion):
    block = notion.root_page.children.add_new(FactoryBlock)
    assert_block_is_okay(**locals(), type="factory")
    assert_block_attributes(block, title="factory", color="blue")


def test_link_to_collection_block(notion):
    block = notion.root_page.children.add_new(LinkToCollectionBlock)
    assert_block_is_okay(**locals(), type="link_to_collection")


def test_numbered_list_block(notion):
    block = notion.root_page.children.add_new(NumberedListBlock)
    assert_block_is_okay(**locals(), type="numbered_list")
    assert_block_attributes(block, title="numbered_list")


def test_page_block(notion):
    block = notion.root_page.children.add_new(PageBlock)
    assert_block_is_okay(**locals(), type="page")
    cover = "/images/page-cover/woodcuts_3.jpg"
    assert_block_attributes(
        block, title="numbered_list", cover=cover, color="blue", icon="✔️"
    )


def test_link_to_page_block(notion):
    block = notion.root_page.children.add_new(LinkToPageBlock)
    assert_block_is_okay(**locals(), type="link_to_page")
    assert_block_attributes(block, title="")


def test_quote_block(notion):
    block = notion.root_page.children.add_new(QuoteBlock)
    assert_block_is_okay(**locals(), type="quote")
    assert_block_attributes(block, title="quote", color="blue")


def test_header_block(notion):
    block = notion.root_page.children.add_new(HeaderBlock)
    assert_block_is_okay(**locals(), type="header")
    assert_block_attributes(block, title="header", color="blue")


def test_sub_header_block(notion):
    block = notion.root_page.children.add_new(SubHeaderBlock)
    assert_block_is_okay(**locals(), type="sub_header")
    assert_block_attributes(block, title="subheader", color="blue")


def test_sub_sub_header_block(notion):
    block = notion.root_page.children.add_new(SubSubHeaderBlock)
    assert_block_is_okay(**locals(), type="sub_sub_header")
    assert_block_attributes(block, title="subsubheader", color="blue")


def test_text_block(notion):
    block = notion.root_page.children.add_new(TextBlock)
    assert_block_is_okay(**locals(), type="text")
    assert_block_attributes(block, title="text", color="blue")


def test_to_do_block(notion):
    block = notion.root_page.children.add_new(ToDoBlock)
    assert_block_is_okay(**locals(), type="to_do")
    assert_block_attributes(block, title="text", color="blue", checked=True)


def test_toggle_block(notion):
    block = notion.root_page.children.add_new(ToggleBlock)
    assert_block_is_okay(**locals(), type="toggle")
    assert_block_attributes(block, title="text", color="blue")
