import json
from threading import Thread
import uuid
from collections import defaultdict
from typing import Callable
from copy import deepcopy
from inspect import signature
from pathlib import Path
from threading import Lock
from typing import Union

from dictdiffer import diff
from tzlocal import get_localzone

from notion.logger import logger
from notion.settings import NOTION_CACHE_DIR
from notion.utils import extract_id, to_list


class MissingClass:
    def __bool__(self):
        return False


Missing = MissingClass()


class Callback:
    def __init__(self, callback: Callable, record, callback_id: str = None, **kwargs):
        self.callback = callback
        self.record = record
        self.callback_id = callback_id or str(uuid.uuid4())
        self.extra_kwargs = kwargs

    def __call__(self, difference, old_val, new_val):
        kwargs = {}
        kwargs.update(self.extra_kwargs)
        kwargs["record"] = self.record
        kwargs["callback_id"] = self.callback_id
        kwargs["difference"] = difference
        kwargs["changes"] = self.record._convert_diff_to_changelist(
            difference, old_val, new_val
        )

        logger.debug(f"Firing callback {self.callback} with kwargs: {kwargs}")

        # trim down the passed parameters
        # to include only those the callback will accept
        params = signature(self.callback).parameters
        if not any(["**" in str(p) for p in params.values()]):
            # there's no "**kwargs" in the callback signature,
            # so remove any unaccepted params
            for arg in kwargs.keys():
                if arg not in params:
                    del kwargs[arg]

        # perform the callback, gracefully handling any exceptions
        try:
            # trigger the callback within its own thread,
            # so it won't block others if it's long-running
            Thread(target=self.callback, kwargs=kwargs, daemon=True).start()
        except Exception as e:
            logger.error(
                f"Error while processing callback for {repr(self.record)}: {repr(e)}"
            )

    def __eq__(self, value: Union["Callback", str]) -> bool:
        if isinstance(value, str):
            return self.callback_id.startswith(value)

        if isinstance(value, Callback):
            return self.callback_id == value.callback_id

        return False


class RecordStore:
    """
    Central Record Store.
    """

    def __init__(self, client, cache_key=None):
        self._mutex = Lock()
        self._client = client
        self._cache_key = cache_key
        self._values = defaultdict(lambda: defaultdict(dict))
        self._role = defaultdict(lambda: defaultdict(str))
        self._collection_row_ids = {}
        self._callbacks = defaultdict(lambda: defaultdict(list))
        self._records_to_refresh = {}
        self._pages_to_refresh = []
        with self._mutex:
            self._load_cache()

    def _get(self, table: str, record_id: str):
        return self._values[table].get(record_id, Missing)

    def _get_cache_path(self, attribute):
        file = f"{self._cache_key}{attribute}.json"
        return str(Path(NOTION_CACHE_DIR) / file)

    def _load_cache(self, attributes=("_values", "_role", "_collection_row_ids")):
        if not self._cache_key:
            return

        for attr in attributes:
            try:
                with open(self._get_cache_path(attr)) as f:
                    if attr == "_collection_row_ids":
                        self._collection_row_ids.update(json.load(f))

                    else:
                        for k, v in json.load(f).items():
                            getattr(self, attr)[k].update(v)

            except (FileNotFoundError, ValueError):
                pass

    def _save_cache(self, attribute):
        if not self._cache_key:
            return

        with open(self._get_cache_path(attribute), "w") as f:
            json.dump(getattr(self, attribute), f)

    def _trigger_callbacks(self, table, record_id, difference, old_val, new_val):
        for callback_obj in self._callbacks[table][record_id]:
            callback_obj(difference, old_val, new_val)

    def set_collection_rows(self, collection_id: str, row_ids):
        if collection_id in self._collection_row_ids:
            old_ids = set(self.get_collection_rows(collection_id))
            new_ids = set(row_ids)
            args = {
                "table": "collection",
                "record_id": collection_id,
                "old_val": old_ids,
                "new_val": new_ids,
            }

            for i in new_ids - old_ids:
                args["difference"] = [("row_added", "rows", i)]
                self._trigger_callbacks(**args)

            for i in old_ids - new_ids:
                args["difference"] = [("row_removed", "rows", i)]
                self._trigger_callbacks(**args)

        self._collection_row_ids[collection_id] = row_ids
        self._save_cache("_collection_row_ids")

    def get_collection_rows(self, collection_id):
        return self._collection_row_ids.get(collection_id, [])

    def get_role(self, table, record_id, force_refresh=False):
        self.get(table, record_id, force_refresh=force_refresh)
        return self._role[table].get(id, None)

    def get(self, table, url_or_id, force_refresh=False):
        rid = extract_id(url_or_id)
        # look up the record in the current local dataset
        result = self._get(table, rid)
        # if it's not found, try refreshing the record from the server
        if result is Missing or force_refresh:
            if table == "block":
                self.call_load_page_chunk(rid)
            else:
                self.call_get_record_values(**{table: rid})
            result = self._get(table, rid)
        return result if result is not Missing else None

    def add_callback(
        self, record, callback: Callable, callback_id=None, **extra_kwargs
    ):
        if not callable(callback):
            raise ValueError(f"The callback {callback} must be a callable.")

        self.remove_callbacks(record._table, record.id, callback_id)
        callback_obj = Callback(
            callback, record, callback_id=callback_id, extra_kwargs=extra_kwargs
        )
        self._callbacks[record._table][record.id].append(callback_obj)
        return callback_obj

    def remove_callbacks(self, table, record_id: str, cb_or_cb_id_prefix=""):
        """
        Remove all callbacks for the record specified
        by `table` and `id` that have a callback_id
        starting with the string `cb_or_cb_id_prefix`,
        or are equal to the provided callback.
        """
        if cb_or_cb_id_prefix is None:
            return

        callbacks = self._callbacks[table][record_id]
        while cb_or_cb_id_prefix in callbacks:
            callbacks.remove(cb_or_cb_id_prefix)

    def _update_record(self, table, record_id, value=None, role=None):
        callback_queue = []

        with self._mutex:
            if role:
                logger.debug(f"Updating 'role' for '{table}/{record_id}' to '{role}'")
                self._role[table][record_id] = role
                self._save_cache("_role")
            if value:
                p_value = json.dumps(value, indent=2)
                logger.debug(
                    f"Updating 'value' for '{table}/{record_id}' to \n{p_value}"
                )
                old_val = self._values[table][record_id]
                difference = list(
                    diff(
                        old_val,
                        value,
                        ignore=["version", "last_edited_time", "last_edited_by"],
                        expand=True,
                    )
                )
                self._values[table][record_id] = value
                self._save_cache("_values")
                if old_val and difference:
                    p_difference = json.dumps(value, indent=2)
                    logger.debug(f"Value changed! Difference:\n{p_difference}")
                    callback = (table, record_id, difference, old_val, value)
                    callback_queue.append(callback)

        # run callbacks outside the mutex to avoid lockups
        for cb in callback_queue:
            self._trigger_callbacks(*cb)

    def call_get_record_values(self, **kwargs):
        """
        Call the server's getRecordValues endpoint
        to update the local record store.
        The keyword arguments map table names into lists
        of (or singular) record IDs to load for that table.
        Use True to refresh all known records for that table.
        """
        requests = []

        for table, ids in kwargs.items():

            # ensure "ids" is a proper list
            if ids:
                ids = list(self._values.get(table, {}).keys())
            ids = to_list(ids)

            # if we're in a transaction, add the requested IDs
            # to a queue to refresh when the transaction completes
            if self._client.in_transaction():
                records = set(self._records_to_refresh.get(table, []) + ids)
                self._records_to_refresh[table] = list(records)
                continue

            requests += [{"table": table, "id": extract_id(i)} for i in ids]

        if requests:
            logger.debug(f"Calling 'getRecordValues' endpoint for requests: {requests}")
            data = {"requests": requests}
            data = self._client.post("getRecordValues", data).json()
            results = data["results"]

            for request, result in zip(requests, results):
                self._update_record(
                    table=request["table"],
                    record_id=request["id"],
                    value=result.get("value"),
                    role=result.get("role"),
                )

    def get_current_version(self, table, record_id):
        values = self._get(table, record_id)
        if values and "version" in values:
            return values["version"]

        return -1

    def call_load_page_chunk(self, page_id):
        if self._client.in_transaction():
            self._pages_to_refresh.append(page_id)
            return

        data = {
            "pageId": page_id,
            "limit": 100000,
            "cursor": {"stack": []},
            "chunkNumber": 0,
            "verticalColumns": False,
        }
        data = self._client.post("loadPageChunk", data).json()
        self.store_record_map(data)

    def store_record_map(self, data: dict) -> dict:
        data = data["recordMap"]
        for table, records in data.items():
            for record_id, record in records.items():
                self._update_record(
                    table=table,
                    record_id=record_id,
                    value=record.get("value"),
                    role=record.get("role"),
                )
        return data

    def call_query_collection(
        self,
        collection_id: str,
        collection_view_id: str,
        search: str = "",
        type: str = "table",
        aggregate: list = None,
        aggregations: list = None,
        filter: dict = None,
        filter_operator: str = "and",
        sort: list = [],
        calendar_by: str = "",
        group_by: str = "",
    ):
        # TODO: No idea what this is.

        if aggregate and aggregations:
            raise ValueError(
                "Use either `aggregate` or `aggregations` (old vs new format)"
            )

        aggregate = to_list(aggregate or [])
        aggregations = aggregations or []
        filter = to_list(filter or {})
        sort = to_list(sort or [])

        data = {
            "collectionId": collection_id,
            "collectionViewId": collection_view_id,
            "loader": {
                "limit": 10000,
                "loadContentCover": True,
                "searchQuery": search,
                "userLocale": "en",
                "userTimeZone": str(get_localzone()),
                "type": type,
            },
            "query": {
                "aggregate": aggregate,
                "aggregations": aggregations,
                "filter": {
                    "filters": filter,
                    "filter_operator": filter_operator,
                },
                "sort": sort,
            },
        }
        data = self._client.post("queryCollection", data).json()
        self.store_record_map(data)

        return data["result"]

    def handle_post_transaction_refreshing(self):
        for block_id in self._pages_to_refresh:
            self.call_load_page_chunk(block_id)
        self._pages_to_refresh = []

        self.call_get_record_values(**self._records_to_refresh)
        self._records_to_refresh = {}

    def run_local_operation(self, table, record_id, path, command, args):
        with self._mutex:
            path = deepcopy(path)
            new_val = deepcopy(self._values[table][record_id])

        ref = new_val

        # loop and descend down the path until it's consumed,
        # or if we're doing a "set", there's one key left
        while (len(path) > 1) or (path and command != "set"):
            comp = path.pop(0)
            if comp not in ref:
                ref[comp] = [] if "list" in command else {}
            ref = ref[comp]

        if not isinstance(ref, dict) and not isinstance(ref, list):
            raise ValueError("IDK ev what")

        if command == "update":
            ref.update(args)

        if command == "set":
            if path:
                ref[path[0]] = args
            else:
                # case for "setting the top level" (i.e. creating a record)
                ref.clear()
                ref.update(args)

        if command == "listAfter":
            if "after" in args:
                ref.insert(ref.index(args["after"]) + 1, args["id"])
            else:
                ref.append(args["id"])

        if command == "listBefore":
            if "before" in args:
                ref.insert(ref.index(args["before"]), args["id"])
            else:
                ref.insert(0, args["id"])

        if command == "listRemove":
            try:
                ref.remove(args["id"])
            except ValueError:
                pass

        self._update_record(table, record_id, value=new_val)
