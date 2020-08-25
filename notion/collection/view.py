from notion.maps import field_map
from notion.record import Record
from notion.collection.query import CollectionQuery


class CollectionView(Record):
    """
    A "view" is a particular visualization of a collection,
    with a "type" (board, table, list, etc) and filters, sort, etc.
    """

    name = field_map("name")
    type = field_map("type")

    @property
    def parent(self):
        return self._client.get_block(self.get("parent_id"))

    def __init__(self, *args, collection, **kwargs):
        self.collection = collection
        super().__init__(*args, **kwargs)

    def build_query(self, **kwargs):
        return CollectionQuery(
            collection=self.collection, collection_view=self, **kwargs
        )

    def default_query(self):
        return self.build_query(**self.get("query", {}))


class CalendarView(CollectionView):
    def build_query(self, **kwargs):
        data = self._client.get_record_data("collection_view", self._id)
        calendar_by = data["query2"]["calendar_by"]
        return super().build_query(calendar_by=calendar_by, **kwargs)


class BoardView(CollectionView):

    group_by = field_map("query.group_by")


class TableView(CollectionView):
    pass


class ListView(CollectionView):
    pass


class GalleryView(CollectionView):
    pass
