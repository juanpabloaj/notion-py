from notion.block.collection.children import CollectionViewBlockViews
from notion.block.media import MediaBlock
from notion.maps import prefixed_field_map


class CollectionViewBlock(MediaBlock):
    """
    Collection View Block.
    """

    _type = "collection_view"
    _str_fields = "title", "collection"

    @property
    def views(self):
        if not hasattr(self, "_views"):
            self._views = CollectionViewBlockViews(parent=self)

        return self._views

    @property
    def collection(self):
        collection_id = self.get("collection_id")

        if not collection_id:
            return None

        if not hasattr(self, "_collection"):
            self._collection = self._client.get_collection(collection_id)

        return self._collection

    @collection.setter
    def collection(self, val):
        if hasattr(self, "_collection"):
            del self._collection

        self.set("collection_id", val.id)

    @property
    def title(self):
        if not hasattr(self, "_collection"):
            return ""

        return self.collection.name

    @title.setter
    def title(self, val):
        self.collection.name = val

    @property
    def description(self):
        if not hasattr(self, "_collection"):
            return ""

        return self.collection.description

    @description.setter
    def description(self, val):
        self.collection.description = val


class CollectionViewPageBlock(CollectionViewBlock):
    """
    Full Page Collection View Block.
    """

    _type = "collection_view_page"

    icon = prefixed_field_map("format.page_icon")
    cover = prefixed_field_map("format.page_cover")


class LinkToCollectionBlock(MediaBlock):
    """
    Link To Collection.
    """

    _type = "link_to_collection"
    # TODO: add custom fields
