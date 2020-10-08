from typing import Union

from notion.block.basic import Block
from notion.block.collection.common import _normalize_query_data, _normalize_prop_name
from notion.utils import extract_id
from notion.block.types import get_collection_query_result_type


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

        klass = get_collection_query_result_type(self.type)

        return klass(
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

    def __repr__(self) -> str:
        children = "\n" if len(self) else ""
        for child in self:
            children += f"  {repr(child)},\n"

        return f"<{self.__class__.__name__} [\n{children}]>"

    def __len__(self) -> int:
        return len(self._block_ids)

    def __getitem__(self, key):
        return list(iter(self))[key]

    def __iter__(self):
        return iter(self._get_block(bid) for bid in self._block_ids)

    def __reversed__(self):
        return reversed(list(self))

    def __contains__(self, other: Union[Block, str]) -> bool:
        return extract_id(other) in self._block_ids

    def _get_block_ids(self, result: dict) -> list:
        return result["blockIds"]

    def _get_block(self, block_id: str):
        from notion.block.collection.basic import CollectionRowBlock

        block = CollectionRowBlock(self.collection._client, block_id)
        # TODO: wtf? pass it as argument?
        block.__dict__["collection"] = self.collection
        return block

    def get_aggregate(self, block_id: str):
        for agg_id, agg in zip(self.aggregate_ids, self.aggregates):
            if block_id == agg_id:
                return agg["value"]
        return None


class CalendarQueryResult(CollectionQueryResult):

    _type = "calendar"

    def _get_block_ids(self, result: dict) -> list:
        return [w["items"] for w in result["weeks"]]


class TableQueryResult(CollectionQueryResult):

    _type = "table"


class BoardQueryResult(CollectionQueryResult):

    _type = "board"


class ListQueryResult(CollectionQueryResult):

    _type = "list"


class GalleryQueryResult(CollectionQueryResult):

    _type = "gallery"
