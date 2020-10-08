from typing import Union

from notion.block.basic import PageBlock
from notion.block.collection.media import CollectionViewPageBlock
from notion.maps import field_map
from notion.record import Record


class NotionSpace(Record):
    """
    Class representing notion's Space - user workplace.
    """

    _type = "space"
    _table = "space"
    _str_fields = "name", "domain"
    _child_list_key = "pages"

    name = field_map("name")
    domain = field_map("domain")
    icon = field_map("icon")

    @property
    def pages(self) -> list:
        # The page list includes pages the current user
        # might not have permissions on, so it's slow to query.
        # Instead, we just filter for pages with the space as the parent.
        return self._client.search_pages_with_parent(self.id)

    @property
    def users(self) -> list:
        ids = [p["user_id"] for p in self.get("permissions")]
        self._client.refresh_records(notion_user=ids)
        return [self._client.get_user(uid) for uid in ids]

    def add_page(
        self, title, type: str = "page", shared: bool = False
    ) -> Union[PageBlock, CollectionViewPageBlock]:
        """
        Create new page.


        Arguments
        ---------
        title : str
            Title for the newly created page.

        type : str, optional
            Type of the page. Must be one of "page" or "collection_view_page".
            Defaults to "page".

        shared : bool, optional
            Whether or not the page should be shared (public).
            TODO: is it true?
            Defaults to False.
        """
        perms = [
            {
                "role": "editor",
                "type": "user_permission",
                "user_id": self._client.current_user.id,
            }
        ]

        if shared:
            perms = [{"role": "editor", "type": "space_permission"}]

        page_id = self._client.create_record(
            "block", self, type=type, permissions=perms
        )
        page = self._client.get_block(page_id)
        page.title = title
        return page
