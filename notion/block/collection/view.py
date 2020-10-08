from notion.block.collection.query import CollectionQuery
from notion.maps import field_map
from notion.record import Record


class CollectionView(Record):
    """
    A "view" is a particular visualization of a collection,
    with a "type" (board, table, list, etc) and filters, sort, etc.
    """

    _type = "collection_view"
    _table = "collection_view"

    name = field_map("name")
    type = field_map("type")

    def __init__(self, *args, collection, **kwargs):
        super().__init__(*args, **kwargs)
        self.collection = collection

    def build_query(self, **kwargs) -> CollectionQuery:
        return CollectionQuery(
            collection=self.collection, collection_view=self, **kwargs
        )

    def default_query(self) -> CollectionQuery:
        """
        Return default query.
        """
        return self.build_query(**self.get("query", {}))

    @property
    def parent(self):
        return self._client.get_block(self.get("parent_id"))


class CalendarView(CollectionView):

    _type = "calendar"

    def build_query(self, **kwargs):
        data = self._client.get_record_data("collection_view", self._id)
        calendar_by = data["query2"]["calendar_by"]
        return super().build_query(calendar_by=calendar_by, **kwargs)


class BoardView(CollectionView):

    _type = "board"

    group_by = field_map("query.group_by")


class TableView(CollectionView):

    _type = "table"


class ListView(CollectionView):

    _type = "list"


class GalleryView(CollectionView):

    _type = "gallery"
