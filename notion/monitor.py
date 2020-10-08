import json
import re
import threading
import time
import uuid
from collections import defaultdict
from typing import Set
from urllib.parse import urlencode

from requests import HTTPError

from notion.block.collection.basic import CollectionBlock
from notion.logger import logger
from notion.record import Record
from notion.settings import MESSAGE_STORE_URL


class Monitor:
    """
    Monitor class for automatic data polling of records.
    """

    thread = None

    def __init__(self, client, root_url: str = MESSAGE_STORE_URL):
        """
        Create Monitor object.


        Arguments
        ---------
        client : NotionClient
            Client to use.

        root_url : str, optional
            Root URL for polling message stats.
            Defaults to valid notion message store URL.
        """
        self.sid = None
        self.client = client
        self.root_url = root_url
        self.session_id = str(uuid.uuid4())
        self._subscriptions = set()
        self.initialize()

    @staticmethod
    def _encode_numbered_json_thing(data: list) -> bytes:
        results = ""
        for obj in data:
            msg = str(len(obj)) + json.dumps(obj, separators=(",", ":"))
            msg = f"{len(msg)}:{msg}"
            results += msg

        return results.encode()

    def _decode_numbered_json_thing(self, thing: bytes) -> list:
        thing = thing.decode().strip()

        for ping in re.findall(r'\d+:\d+"primus::ping::\d+"', thing):
            logger.debug(f"Received ping: {ping}")
            self.post_data(ping.replace("::ping::", "::pong::"))

        results = []
        for blob in re.findall(r"\d+:\d+({.+})(?=\d|$)", thing):
            results.append(json.loads(blob))

        if thing and not results and "::ping::" not in thing:
            logger.debug(f"Could not parse monitoring response: {thing}")

        return results

    def _refresh_updated_records(self, events: list):
        records_to_refresh = defaultdict(list)
        versions_pattern = re.compile(r"versions/([^:]+):(.+)")
        collection_pattern = re.compile(r"collection/(.+)")

        events = filter(lambda e: isinstance(e, dict), events)
        events = filter(lambda e: e.get("type", "") == "notification", events)

        for event in events:
            logger.debug(f"Received the following event from notion: {event}")
            key = event.get("key")

            # TODO: rewrite below if cases to something simpler
            if key.startswith("versions/"):
                match = versions_pattern.match(key)
                if not match:
                    continue

                record_id, record_table = match.groups()
                name = f"{record_table}/{record_id}"
                new = event["value"]
                old = self.client._store.get_current_version(
                    table=record_table, record_id=record_id
                )

                if new > old:
                    logger.debug(
                        (
                            f"Record {name} has changed; refreshing to update"
                            f"from version {old} to version {new}"
                        )
                    )
                    records_to_refresh[record_table].append(record_id)
                else:
                    logger.debug(
                        (
                            f"Record {name} already at version {old}"
                            f"not trying to update to version {new}"
                        )
                    )

            if key.startswith("collection/"):

                match = collection_pattern.match(key)
                if not match:
                    continue

                collection_id = match.groups()[0]

                self.client.refresh_collection_rows(collection_id)
                row_ids = self.client._store.get_collection_rows(collection_id)

                logger.debug(
                    (
                        f"Something inside collection '{collection_id}' "
                        f"has changed. Refreshing all {row_ids} rows inside it"
                    )
                )

                records_to_refresh["block"] += row_ids

        self.client.refresh_records(**records_to_refresh)

    def url(self, **kwargs) -> str:
        kwargs["b64"] = 1
        kwargs["transport"] = kwargs.get("transport", "polling")
        kwargs["sessionId"] = kwargs.get("sessionId", self.session_id)
        return f"{self.root_url}?{urlencode(kwargs)}"

    def initialize(self):
        """
        Initialize the monitoring session.
        """
        logger.debug("Initializing new monitoring session.")

        content = self.client.session.get(self.url(EIO=3)).content
        self.sid = self._decode_numbered_json_thing(content)[0]["sid"]

        logger.debug(f"New monitoring session ID is: {self.sid}")

        # resubscribe to any existing subscriptions if we're reconnecting
        old_subscriptions = self._subscriptions
        self._subscriptions = set()
        self.subscribe(old_subscriptions)

    def subscribe(self, records: Set[Record]):
        """
        Subscribe to changes of passed records.


        Arguments
        ---------
        records : set of Record
            Set of `Record` objects to subscribe to.
        """
        if isinstance(records, list):
            records = set(records)

        # TODO: how to describe that you can also pass
        #       record explicitly or should we block it?
        if not isinstance(records, set):
            records = {records}

        sub_data = []

        for record in records.difference(self._subscriptions):
            key = f"{record.id}:{record._table}"
            logger.debug(f"Subscribing new record: {key}")

            # save it in case we're disconnected
            self._subscriptions.add(record)

            # TODO: hide that dict generation in Record class
            sub_data.append(
                {
                    "type": "/api/v1/registerSubscription",
                    "requestId": str(uuid.uuid4()),
                    "key": f"versions/{key}",
                    "version": record.get("version", -1),
                }
            )

            # if it's a collection, subscribe to changes to its children too
            if isinstance(record, CollectionBlock):
                sub_data.append(
                    {
                        "type": "/api/v1/registerSubscription",
                        "requestId": str(uuid.uuid4()),
                        "key": f"collection/{record.id}",
                        "version": -1,
                    }
                )

        self.post_data(self._encode_numbered_json_thing(sub_data))

    def post_data(self, data: bytes):
        """
        Send monitoring requests to Notion.


        Arguments
        ---------
        data : bytes
            Form encoded request data.
        """
        if not data:
            return

        logger.debug(f"Posting monitoring data: {data}")
        self.client.session.post(self.url(sid=self.sid), data=data)

    def poll(self, retries: int = 10):
        """
        Poll for changes.


        Arguments
        ---------
        retries : int, optional
            Number of times to retry request if it fails.
            Should be bigger than 5.
            Defaults to 10.


        Raises
        ------
        HTTPError
            When GET request fails for `retries` times.
        """
        logger.debug("Starting new long-poll request")
        url = self.url(EIO=3, sid=self.sid)
        response = None

        while retries:
            try:
                retries -= 1
                response = self.client.session.get(url)
                response.raise_for_status()

            except HTTPError as e:
                try:
                    message = f"{response.content} / {e}"
                except AttributeError:
                    message = str(e)

                logger.warn(
                    "Problem with submitting poll request: "
                    f"{message} (will retry {retries} more times)"
                )

                time.sleep(0.1)
                if retries <= 0:
                    raise

                if retries <= 5:
                    logger.error(
                        "Persistent error submitting poll request: "
                        f"{message} (will retry {retries} more times)"
                    )

                if retries == 3:
                    # if we're close to giving up, try to restart the session
                    self.initialize()

        self._refresh_updated_records(
            self._decode_numbered_json_thing(response.content)
        )

    def poll_async(self):
        if self.thread:
            # Already polling async; no need to have two threads
            return

        logger.debug("Starting new thread for async polling")
        self.thread = threading.Thread(target=self.poll_forever, daemon=True)
        self.thread.start()

    def poll_forever(self):
        """
        Call `poll()` in never-ending loop with small time intervals in-between.

        This function is blocking, it never returns!
        """
        while True:
            try:
                self.poll()
            except Exception as e:
                logger.error("Encountered error during polling!")
                logger.error(e, exc_info=True)
                time.sleep(1)
