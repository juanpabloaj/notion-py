import os
from dataclasses import dataclass

import pytest

from notion.block.basic import Block
from notion.client import NotionClient


@dataclass
class NotionTestContext:
    client: NotionClient
    root_page: Block


@pytest.fixture
def notion(_cache=[]):
    if _cache:
        return _cache[0]

    token_v2 = os.environ["NOTION_TOKEN_V2"].strip()
    page_url = os.environ["NOTION_PAGE_URL"].strip()

    client = NotionClient(token_v2=token_v2)
    page = client.get_block(page_url)

    if page is None:
        raise ValueError(f"No such page under url: {page_url}")

    # clean the page for new tests
    for child in page.children:
        child.remove(permanently=True)

    page.refresh()

    _cache.append(NotionTestContext(client, page))
    return _cache[0]


def assert_block_is_okay(notion, block, type: str, parent=None):
    parent = parent or notion.root_page

    assert block.id
    assert block.type == type
    assert block.alive is True
    assert block.is_alias is False
    assert block.parent == parent


def assert_block_attributes(block, **kwargs):
    for attr, value in kwargs.items():
        assert hasattr(block, attr)
        setattr(block, attr, value)

    block.refresh()

    for attr, value in kwargs.items():
        assert getattr(block, attr) == value
