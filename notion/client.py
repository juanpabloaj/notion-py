import hashlib
import json
import os
import re
import time
import uuid
from typing import Union, Optional
from urllib.parse import urljoin
from zipfile import ZipFile

from requests import Session, get, Response
from requests.adapters import HTTPAdapter
from requests.cookies import cookiejar_from_dict
from urllib3.util.retry import Retry

from notion.block.basic import Block
from notion.block.collection.basic import (
    CollectionBlock,
    TemplateBlock,
    CollectionRowBlock,
)
from notion.block.collection.view import CollectionView
from notion.block.types import get_block_type, get_collection_view_type
from notion.logger import logger
from notion.monitor import Monitor
from notion.operations import operation_update_last_edited, build_operations
from notion.settings import API_BASE_URL
from notion.space import NotionSpace
from notion.store import RecordStore
from notion.user import NotionUser
from notion.utils import extract_id, now, to_list


class NotionApiError(Exception):
    def __init__(self, message: str, **extra):
        dumped_data = json.dumps(extra, indent=2)
        logger.error(f"Exception: {dumped_data}")
        super().__init__(message)


class InvalidCollectionViewUrl(NotionApiError):
    pass


class NotionValidationError(NotionApiError):
    pass


class NotionUnauthorizedError(NotionApiError):
    pass


class Transaction:
    """
    Transaction object.
    """

    _is_nested = False

    def __init__(self, client):
        """
        Create Transaction object.

        Arguments
        ---------
        client : NotionClient
            Client object to use for transaction.
        """
        self.client = client

    def __enter__(self):
        if hasattr(self.client, "_transaction_operations"):
            # client is already in a transaction, so we'll just
            # make this one a no-op and let the outer one handle it
            self._is_nested = True
            return

        self.client._transaction_operations = []
        self.client._pages_to_refresh = []
        self.client._blocks_to_refresh = []

    def __exit__(self, exc_type, exc_value, traceback):
        if self._is_nested:
            return

        operations = getattr(self.client, "_transaction_operations")
        delattr(self.client, "_transaction_operations")

        if not exc_type:
            # submit the transaction if there was no exception
            self.client.submit_transaction(operations=operations)

        self.client._store.handle_post_transaction_refreshing()


class NotionClient:
    """
    This is the entry point to using the API.

    Create an instance of this class, passing it
    the value of the "token_v2" cookie from a logged-in
    browser session on Notion.so.
    """

    def __init__(
        self,
        token_v2: str = "",
        enable_monitoring: bool = False,
        start_monitoring: bool = False,
        enable_caching: bool = False,
        cache_key: str = "",
    ):
        """
        Create NotionClient object and fill its fields.


        Arguments
        ---------
        token_v2 : str, optional
            The cookie from logged-in browser session on notion.so.
            If not provided then all operations will be ran as if user
            was not logged in.
            Defaults to empty string.

        enable_monitoring : bool, optional
            Whether or not to monitor the records managed by NotionClient.
            Defaults to False.

        start_monitoring : bool, optional
            Whether or not to start monitoring immediately upon logging in.
            This option takes effect only when `monitor` is True.
            Defaults to False.

        enable_caching : bool, optional
            Whether or not to enable caching of fetched data to file.
            Defaults to False.

        cache_key : str, optional
            The key string used for storing all cached data in file.
            This option takes effect only when `enable_caching` is True.
            Defaults to SHA256 of token_v2.
        """
        self.session = self._create_session(token_v2)

        # noinspection InsecureHash
        cache_key = cache_key or hashlib.sha256(token_v2.encode()).hexdigest()
        cache_key = cache_key if enable_caching else None
        self._store = RecordStore(self, cache_key=cache_key)

        self._monitor = None
        if enable_monitoring:
            self._monitor = Monitor(self)
            if start_monitoring:
                self.start_monitoring()

        if token_v2:
            self._update_user_info()

    @staticmethod
    def _create_session(token_v2: str = "") -> Session:
        """
        Helper method for creating a session object for API requests.


        Arguments
        ---------
        token_v2 : str, optional
            Token to use for creating User session.
            Defaults to empty string.


        Returns
        -------
        Session
            initialised Session object.
        """
        retry = Retry(
            total=5,
            backoff_factor=0.3,
            status_forcelist=(502, 503),
            method_whitelist=(
                "POST",
                "HEAD",
                "TRACE",
                "GET",
                "PUT",
                "OPTIONS",
                "DELETE",
            ),
        )

        session = Session()
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.cookies = cookiejar_from_dict({"token_v2": token_v2})

        return session

    @staticmethod
    def _download_url(url: str, save_path: str, chunk_size: int = 128):
        """
        Download the zip file and save it to a file.


        Arguments
        ---------
        url : str
            URL from which to download.

        save_path : str
            File name to output the zip file into.

        chunk_size : int, optional
            Size of the downloaded chunk.
            If set to 0 then the data will be read as it arrives
            in whatever the size the chunks are received.
            Defaults to 128.


        https://requests.readthedocs.io/en/master/user/quickstart/#raw-response-content
        """
        r = get(url, stream=True)
        with open(save_path, "wb") as fd:
            for chunk in r.iter_content(chunk_size=chunk_size or None):
                fd.write(chunk)

    @staticmethod
    def _unzip_file(file_name: str, delete: bool = True):
        """
        Helper method to unzip the zipped file.


        Arguments
        ---------
        file_name : str
            File name of the ZIP to unpack.

        delete : bool, optional
            Whether or not to remove the file after unpacking.
            Defaults to True.
        """
        with ZipFile(file_name) as f:
            f.extractall()

        if delete:
            os.remove(file_name)

    @staticmethod
    def _maybe_prefix_url(endpoint: str) -> str:
        if endpoint.startswith("http"):
            return endpoint

        return urljoin(API_BASE_URL, endpoint)

    def _update_user_info(self) -> dict:
        """
        Reload information about a Notion User.


        Returns
        -------
        dict
            User data.
        """
        data = self.post("loadUserContent").json()
        data = self._store.store_record_map(data)

        first_user = list(data["notion_user"].keys())[0]
        first_space = list(data["space"].keys())[0]
        self.current_user = self.get_user(first_user)
        self.current_space = self.get_space(first_space)

        return data

    def get_top_level_pages(self) -> list:
        """
        Get list of top level pages defined in Notion Workspace.


        Returns
        -------
        list of Block
            Top level pages.
        """
        blocks = self._update_user_info()["block"].keys()
        return [self.get_block(bid) for bid in blocks]

    def get_record_data(
        self, table: str, url_or_id: str, force_refresh: bool = False
    ) -> dict:
        """
        Get record data.


        Arguments
        ---------
        table : str
            A "block type" in notion.so terminology.

        url_or_id : str
            Path or ID to block.

        force_refresh : bool, optional
            Whether or not to force a refresh of data.
            Defaults to False.


        Returns
        -------
        dict
            Record data.
        """
        return self._store.get(
            table=table, url_or_id=url_or_id, force_refresh=force_refresh
        )

    def get_block(self, url_or_id: str, force_refresh: bool = False) -> Optional[Block]:
        """
        Retrieve an instance of a subclass of Block that maps to
        the block/page identified by the URL or ID passed in.


        Arguments
        ---------
        url_or_id : str
            Path or ID to block.

        force_refresh : bool, optional
            Whether or not to force a refresh of data.
            Defaults to False.


        Returns
        -------
        Block or None
            Found block or None.
        """
        block_id = extract_id(url_or_id)
        block = self.get_record_data("block", block_id, force_refresh)

        if not block:
            return None

        if block.get("parent_table") == "collection":
            if block.get("is_template"):
                klass = TemplateBlock
            else:
                klass = CollectionRowBlock
        else:
            klass = get_block_type(block.get("type"))

        return klass(client=self, block_id=block_id)

    def get_collection(
        self, collection_id: str, force_refresh: bool = False
    ) -> Optional[CollectionBlock]:
        """
        Retrieve an instance of Collection that maps to
        the collection identified by the ID passed in.


        Arguments
        ---------
        collection_id : str
            ID of searched collection.

        force_refresh : bool, optional
            Whether or not to force a refresh of data.
            Defaults to False.


        Returns
        -------
        CollectionBlock
            Found collection or None.
        """
        record_data = self.get_record_data(
            "collection", collection_id, force_refresh=force_refresh
        )

        if record_data:
            return CollectionBlock(self, collection_id)

    def get_collection_view(
        self,
        url_or_id: str,
        collection: CollectionBlock = None,
        force_refresh: bool = False,
    ) -> Optional[CollectionView]:
        """
        Retrieve an instance of a subclass of CollectionView
        that maps to the appropriate type.

        The `url_or_id` argument can either be the URL
        for a database page, or the ID of a collection_view
        (in which case you must pass the collection)


        Arguments
        ---------
        url_or_id : str
            ID of searched collection view.

        collection : Collection
            object representing ID of searched collection view.

        force_refresh : bool, optional
            Whether or not to force a refresh of data.
            Defaults to False.


        Raises
        ------
        InvalidCollectionViewUrl
            When passed in URL is invalid.


        Returns
        -------
        CollectionView
            Found collectionView or None.
        """
        if url_or_id.startswith("http"):
            # if it's a URL for a database page,
            # try extracting the collection and view IDs
            match = re.search(r"([a-f0-9]{32})\?v=([a-f0-9]{32})", url_or_id)
            if not match:
                raise InvalidCollectionViewUrl(
                    f"Could not find valid ID in URL '{url_or_id}'"
                )

            collection_id, view_id = match.groups()
            collection = self.get_collection(collection_id, force_refresh)
        else:
            view_id = url_or_id

            if collection is None:
                raise ValueError(
                    "If 'url_or_id' is an ID (not a URL), "
                    "you must also pass the 'collection'"
                )

        view = self.get_record_data(
            "collection_view", view_id, force_refresh=force_refresh
        )

        if view:
            klass = get_collection_view_type(view.get("type", ""))
            return klass(self, view_id, collection=collection)

    def get_user(
        self, user_id: str, force_refresh: bool = False
    ) -> Optional[NotionUser]:
        """
        Retrieve an instance of User that maps to
        the notion_user identified by the ID passed in.


        Arguments
        ---------
        user_id : str
            ID of searched user.

        force_refresh : bool, optional
            Whether or not to force a refresh of data.
            Defaults to False.


        Returns
        -------
        NotionUser
            Found user or None.
        """
        user = self.get_record_data("notion_user", user_id, force_refresh)
        if user:
            return NotionUser(self, user_id)

    def get_space(
        self, space_id: str, force_refresh: bool = False
    ) -> Optional[NotionSpace]:
        """
        Retrieve an instance of Space that maps to
        the space identified by the ID passed in.


        Arguments
        ---------
        space_id : str
            ID of searched user.

        force_refresh : bool, optional
            Whether or not to force a refresh of data.
            Defaults to False.


        Returns
        -------
        NotionSpace
            Found space or None.
        """
        space = self.get_record_data("space", space_id, force_refresh)
        if space:
            return NotionSpace(self, space_id)

    def start_monitoring(self):
        """
        Start monitoring the tracked blocks.

        This function will create new Thread.
        """
        self._monitor.poll_async()

    def refresh_records(self, **kwargs):
        """
        The keyword arguments map table names into
        lists of (or singular) record IDs to load for that table.

        Use `True` instead of a list to refresh
        all known records for that table.
        """
        self._store.call_get_record_values(**kwargs)

    def refresh_collection_rows(self, collection_id: str):
        """
        Refresh collection rows.


        Arguments
        ---------
        collection_id : str
            ID of the collection.
        """
        collection = self.get_collection(collection_id)
        row_ids = [row.id for row in collection.get_rows()]
        self._store.set_collection_rows(collection_id, row_ids)

    def download_block(
        self,
        block_id: str,
        recursive: bool = False,
        export_type: str = "markdown",
        time_zone: str = "America/Chicago",
        locale: str = "en",
    ):
        """
        Download block.

        TODO: Add support for downloading a list of blocks.


        Arguments
        ---------
        block_id : str
            ID of the block.

        recursive : bool, optional
            Whether or not to include sub pages.
            Defaults to False.

        export_type : str
            Type of the output file.
            The options are "markdown", "pdf", "html".
            Defaults to "markdown".

        time_zone : str, optional
            I don't know what values go here. I'm in the Chicago
            timezone (central) and this is what I saw in the request.
            Defaults to "America/Chicago".
            TODO: test? hard code?

        locale : str, optional
            Locale for the export.
            Defaults to "en".
        """
        data = {
            "task": {
                "eventName": "exportBlock",
                "request": {
                    "blockId": block_id,
                    "recursive": recursive,
                    "exportOptions": {
                        "exportType": export_type,
                        "timeZone": time_zone,
                        "locale": locale,
                    },
                },
            }
        }

        if export_type in ["pdf", "html"]:
            data["task"]["request"]["exportOptions"]["pdfFormat"] = "Letter"

        def fetch():
            time.sleep(0.1)
            return self.post("getTasks", {"taskIds": task_ids}).json()

        task_ids = [self.post("enqueueTask", data).json()["taskId"]]
        task = fetch()

        # Ensure that we're getting the data when it's ready.
        while "status" not in task["results"][0]:
            task = fetch()

        while "exportURL" not in task["results"][0]["status"]:
            task = fetch()

        tmp_zip = f"{block_id}.zip"
        url = task["results"][0]["status"]["exportURL"]
        self._download_url(url, tmp_zip)
        self._unzip_file(tmp_zip)

    def get(self, endpoint: str) -> Response:
        """
        Send HTTP GET request to given endpoint or URL.

        Arguments
        ---------
        endpoint : str
            Notion's endpoint to aim at.

        Returns
        -------
        Response
            Whatever API sent back.
        """
        url = self._maybe_prefix_url(endpoint)
        return self.session.get(url=url)

    def put(self, endpoint: str, data: dict = None, **kwargs) -> Response:
        """
        Send HTTP PUT request to given endpoint or URL.

        Arguments
        ---------
        endpoint : str
            Notion's endpoint to aim at.

        data : dict
            Data to send.
            Defaults to None.

        kwargs : dict
            Additional params for put().
            Defaults to empty dict.


        Returns
        -------
        Response
            Whatever API sent back.
        """
        url = self._maybe_prefix_url(endpoint)
        return self.session.put(url=url, data=data, **kwargs)

    def post(self, endpoint: str, data: dict = None, **kwargs) -> Response:
        """
        Send HTTP POST request to given endpoint or URL.

        All API requests on Notion.so are done as POSTs,
        except the websocket communications.


        Arguments
        ---------
        endpoint : str
            Notion's endpoint to aim at.

        data : dict
            Data to send.
            Defaults to empty dict.

        kwargs : dict
            Additional params to post().
            Defaults to empty dict.


        Raises
        ------
        NotionValidationError
            When POST fails with HTTP 400.

        NotionUnauthorizedError
            When POST fails with HTTP 401.

        NotionApiError
            When POST fails in a different way.


        Returns
        -------
        Response
            Whatever API sent back.
        """
        url = self._maybe_prefix_url(endpoint)
        resp = self.session.post(url, json=data or {}, **kwargs)
        code = resp.status_code
        res_data = resp.json()

        if code < 400:
            return resp

        msg = res_data.get("message") or "<message was not provided>"

        if code == 400:
            raise NotionValidationError(msg, extra=res_data)

        if code == 401:
            raise NotionUnauthorizedError(msg, extra=res_data)

        raise NotionApiError(msg, extra=res_data)

    def submit_transaction(
        self, operations: Union[list, dict], update_last_edited: bool = True
    ):
        """
        Submit list of operations in atomic transaction block.


        Arguments
        ---------
        operations : list or dict
            List of operations to submit.

        update_last_edited : bool, optional
            Whether or not to automatically update last edited records.
            Defaults to True.
        """
        if not operations:
            return

        operations = to_list(operations)

        if update_last_edited:
            updated_blocks = set(
                [op["id"] for op in operations if op["table"] == "block"]
            )
            operations += [
                operation_update_last_edited(self.current_user.id, block_id)
                for block_id in updated_blocks
            ]

        if self.in_transaction():
            # TODO: fix that stuff, shouldn't look like that
            ops = getattr(self, "_transaction_operations") + operations
            setattr(self, "_transaction_operations", ops)

        else:
            self.post("submitTransaction", data={"operations": operations})
            for operation in operations:
                operation["record_id"] = operation.pop("id")
                self._store.run_local_operation(**operation)

    def build_and_submit_transaction(self, *args, **kwargs):
        self.submit_transaction(build_operations(*args, **kwargs))

    def as_atomic_transaction(self) -> Transaction:
        """
        Returns a context manager that buffers up all calls
        to `submit_transaction` and sends them as one
        big transaction when the context manager exits.


        Returns
        -------
        Transaction
            Initialised transaction object.
        """
        return Transaction(client=self)

    def in_transaction(self) -> bool:
        """
        Returns True if we're currently in a transaction, otherwise False.
        """
        return hasattr(self, "_transaction_operations")

    def search_pages_with_parent(
        self, parent_id: str, search: str = "", limit: int = 10000
    ) -> list:
        """
        Search for pages with parent.


        Arguments
        ---------
        parent_id : str
            ID of parent block.

        search : str, optional
            Text to search by.
            Defaults to empty string.

        limit : int, optional
            Max number of pages to return.
            Defaults to 10_000.


        Returns
        -------
        list
            List of results.
        """
        data = {
            "query": search,
            "parentId": parent_id,
            "spaceId": self.current_space.id,
            "limit": limit,
        }
        data = self.post("searchPagesWithParent", data).json()
        self._store.store_record_map(data)

        return data["results"]

    def search_blocks(self, search: str, limit: int = 25) -> list:
        """
        Search for blocks.


        Arguments
        ---------
        search : str
            Text to search by.

        limit : int, optional
            Max number of blocks to return.
            Defaults to 25.


        Returns
        -------
        list
            List of blocks.
        """
        data = {
            "query": search,
            "table": "space",
            "id": self.current_space.id,
            "limit": limit,
        }
        data = self.post("searchBlocks", data).json()
        self._store.store_record_map(data)

        return [self.get_block(bid) for bid in data["results"]]

    def create_record(self, table: str, parent: Block, **kwargs) -> str:
        """
        Create new record.


        Arguments
        ---------
        table : str
            Table value.

        parent : Block
            Parent for the newly created record.


        Returns
        -------
        str
            ID of newly created record.
        """
        # make up a new UUID; apparently we get to choose our own!
        record_id = str(uuid.uuid4())
        child_list_key = kwargs.get("child_list_key") or parent._child_list_key

        args = {
            "id": record_id,
            "version": 1,
            "alive": True,
            "created_by": self.current_user.id,
            "created_time": now(),
            "parent_id": parent.id,
            "parent_table": parent._table,
            **kwargs,
        }

        with self.as_atomic_transaction():
            self.build_and_submit_transaction(
                record_id=record_id, path="", args=args, command="set", table=table
            )

            # add the record to the content list of the parent, if needed
            if child_list_key:
                self.build_and_submit_transaction(
                    record_id=parent.id,
                    path=child_list_key,
                    args={"id": record_id},
                    command="listAfter",
                    table=parent._table,
                )

        return record_id
