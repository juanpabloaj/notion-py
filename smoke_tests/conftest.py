import os
from dataclasses import dataclass

import pytest

from notion.block.common import Block
from notion.client import NotionClient


@dataclass
class NotionTestContext:
    client: NotionClient
    root_page: Block


@pytest.fixture
def notion(cache=[]):
    if cache:
        return cache[0]

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

    cache.append(NotionTestContext(client, page))
    return cache[0]
