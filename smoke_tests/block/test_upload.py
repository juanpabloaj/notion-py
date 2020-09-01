from notion.block.upload import PdfBlock, ImageBlock, VideoBlock, FileBlock
from smoke_tests.conftest import assert_block_is_okay, assert_block_attributes


def test_file_block(notion):
    block = notion.root_page.children.add_new(FileBlock)
    assert_block_is_okay(**locals(), type="file")

    assert block.title == ""
    assert block.source == ""
    assert block.file_id is None

    title = "requirements.txt"
    block.upload_file(title)
    block.title = title
    block.refresh()

    assert block.title == title
    assert "secure.notion-static.com" in block.source
    assert len(block.file_id) == 36


def test_image_block(notion):
    block = notion.root_page.children.add_new(ImageBlock)
    assert_block_is_okay(**locals(), type="image")
    source = "https://raw.githubusercontent.com/jamalex/"
    source = source + "notion-py/master/ezgif-3-a935fdcb7415.gif"
    assert_block_attributes(block, source=source, caption="caption")


def test_video_block(notion):
    block = notion.root_page.children.add_new(VideoBlock)
    assert_block_is_okay(**locals(), type="video")
    source = "https://streamable.com/8ud2kh"
    assert_block_attributes(block, source=source, caption="caption")


def test_pdf_block(notion):
    block = notion.root_page.children.add_new(PdfBlock)
    assert_block_is_okay(**locals(), type="pdf")
