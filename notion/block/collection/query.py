from notion.block.basic import Block
from notion.block.collection.basic import CollectionViewBlock
from notion.block.collection.common import _normalize_query_data, _normalize_prop_name
from notion.utils import extract_id
from notion.block.types import collection_query_result_types


class CollectionQuery:
    """
    Collection Query.
    """

    def __init__(
        self,
        collection,
        collection_view,
        search="",
        type="table",
        aggregate=[],
        aggregations=[],
        filter=[],
        sort=[],
        calendar_by="",
        group_by="",
    ):
        # TODO: replace all these arguments with something sane
        if aggregate and aggregations:
            raise ValueError(
                "Use only one of `aggregate` or `aggregations` (old vs new format)"
            )

        self.collection = collection
        self.collection_view = collection_view
        self.search = search
        self.type = type
        self.aggregate = _normalize_query_data(aggregate, collection)
        self.aggregations = _normalize_query_data(aggregations, collection)
        self.filter = _normalize_query_data(filter, collection)
        self.sort = _normalize_query_data(sort, collection)
        self.calendar_by = _normalize_prop_name(calendar_by, collection)
        self.group_by = _normalize_prop_name(group_by, collection)
        self._client = collection._client

    def execute(self) -> "CollectionQueryResult":
        """
        Execute the query.


        Returns
        -------
        CollectionQueryResult
            Result of the query.
        """

        result_class = collection_query_result_types().get(
            self.type, CollectionQueryResult
        )

        return result_class(
            self.collection,
            self._client._store.call_query_collection(
                collection_id=self.collection.id,
                collection_view_id=self.collection_view.id,
                search=self.search,
                type=self.type,
                aggregate=self.aggregate,
                aggregations=self.aggregations,
                filter=self.filter,
                sort=self.sort,
                calendar_by=self.calendar_by,
                group_by=self.group_by,
            ),
            self,
        )


class CollectionQueryResult:
    """
    Collection Query Result.
    """

    _type = ""

    def __init__(self, collection, result, query: CollectionQuery):
        self._block_ids = self._get_block_ids(result)
        self.collection = collection
        self.query = query
        self.aggregates = result.get("aggregationResults", [])
        self.aggregate_ids = [
            agg.get("id") for agg in (query.aggregate or query.aggregations)
        ]

    def _get_block_ids(self, result):
        return result["blockIds"]

    def _get_block(self, id):
        block = CollectionViewBlock(self.collection._client, id)
        # TODO: wtf? pass it as argument?
        block.__dict__["collection"] = self.collection
        return block

    def get_aggregate(self, id):
        for agg_id, agg in zip(self.aggregate_ids, self.aggregates):
            if id == agg_id:
                return agg["value"]
        return None

    def __repr__(self):
        if not len(self):
            return "[]"

        children = ""
        for child in self:
            children += f"  {repr(child)},\n"

        return f"[\n{children}]"

    def __len__(self):
        return len(self._block_ids)

    def __getitem__(self, key):
        return list(iter(self))[key]

    def __iter__(self):
        return iter(self._get_block(bid) for bid in self._block_ids)

    def __reversed__(self):
        # TODO: Unexpected type(s): (Iterator) Possible types: (Reversible) (Sequence)
        return reversed(iter(self))

    def __contains__(self, item):
        if isinstance(item, str):
            item_id = extract_id(item)
        elif isinstance(item, Block):
            item_id = item.id
        else:
            return False
        return item_id in self._block_ids


class CalendarQueryResult(CollectionQueryResult):

    _type = "calendar"

    def _get_block_ids(self, result):
        block_ids = []
        for week in result["weeks"]:
            block_ids += week["items"]
        return block_ids


class TableQueryResult(CollectionQueryResult):

    _type = "table"


class BoardQueryResult(CollectionQueryResult):

    _type = "board"


class ListQueryResult(CollectionQueryResult):

    _type = "list"


class GalleryQueryResult(CollectionQueryResult):

    _type = "gallery"
