import uuid
from datetime import datetime
from typing import Union, Iterable, Any
from urllib.parse import urlparse, parse_qs, quote_plus, unquote_plus

import requests
from bs4 import BeautifulSoup
from slugify import slugify as _dash_slugify

from notion.settings import (
    BASE_URL,
    SIGNED_URL_PREFIX,
    S3_URL_PREFIX,
    S3_URL_PREFIX_ENCODED,
    EMBED_API_URL,
)


class InvalidNotionIdentifier(Exception):
    """
    Invalid Notion Identifier was found.
    """

    pass


def now() -> int:
    """
    Get UNIX-style time since epoch in seconds.


    Returns
    -------
    int
        Time since epoch in seconds.
    """
    return int(datetime.now().timestamp() * 1000)


def extract_id(url_or_id: str) -> str:
    """
    Extract the block/page ID from a Notion.so URL.

    If it's a bare page URL, it will be the ID of the page.
    If there's a hash with a block ID in it (from clicking "Copy Link")
    on a block in a page), it will instead be the ID of that block.
    If it's already in ID format, it will be passed right through.


    Arguments
    ---------
    url_or_id : str
        Link to block or its ID.


    Raises
    ------
    InvalidNotionIdentifier
        Raised when `url_or_id` can't be converted to UUID.


    Returns
    -------
    str
        ID of the block.
    """
    original_url_or_id = url_or_id

    if url_or_id.startswith(BASE_URL):
        url_or_id = (
            url_or_id.split("#")[-1]
            .split("/")[-1]
            .split("&p=")[-1]
            .split("?")[0]
            .split("-")[-1]
        )

    try:
        return str(uuid.UUID(url_or_id))
    except ValueError:
        raise InvalidNotionIdentifier(original_url_or_id)


def get_embed_data(source_url: str) -> dict:
    """
    Get embed data.


    Arguments
    ---------
    source_url : str
        Source URL from which the embedded data will be extracted.


    Returns
    -------
    dict
        Extracted data.
    """
    return requests.get(f"{EMBED_API_URL}&url={source_url}").json()


def get_embed_link(source_url: str) -> str:
    """
    Get embed link.


    Arguments
    ---------
    source_url : str
        Source URL from which the embedded link will be extracted.


    Returns
    -------
    str
        Extracted link.
    """

    data = get_embed_data(source_url)

    if "html" not in data:
        return source_url

    # TODO: replace BS4 with built in solution
    url = list(BeautifulSoup(data["html"], "html.parser").children)[0]["src"]

    return parse_qs(urlparse(url).query)["src"][0]


def add_signed_prefix_as_needed(url: str, client=None) -> str:
    """
    Utility function for adding signed prefix to URL.


    Arguments
    ---------
    url : str
        URL to operate on.

    client : NotionClient, optional
        # TODO: Client object, used for ???
        Defaults to None.


    Returns
    -------
    str
        Prefixed URL.
    """
    if not url:
        return ""

    if url.startswith(S3_URL_PREFIX):
        url = SIGNED_URL_PREFIX + quote_plus(url)
        if client:
            url = client.session.head(url).headers.get("Location")

    return url


def remove_signed_prefix_as_needed(url: str) -> str:
    """
    Utility function for removing signed prefix from URL.


    Arguments
    ---------
    url : str
        URL to operate on.


    Returns
    -------
    str
        Non-prefixed URL.
    """
    if not url:
        return ""

    if url.startswith(SIGNED_URL_PREFIX):
        return unquote_plus(url[len(S3_URL_PREFIX) :])

    if url.startswith(S3_URL_PREFIX_ENCODED):
        parsed = urlparse(url.replace(S3_URL_PREFIX_ENCODED, S3_URL_PREFIX))
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    return url


def slugify(original: str) -> str:
    """
    Convert text to computer-friendly simplified form.


    Arguments
    ---------
    original : str
        String to operate on.


    Returns
    -------
    str
        Converted string.
    """
    return _dash_slugify(original).replace("-", "_")


def get_by_path(path: Union[Iterable, str], obj: Any, default: Any = None):
    """
    Get value from object's key by dotted path (i.e. "path.to.some.key").


    Arguments
    ---------
    path : list or str
        Path in string form or as list elements.

    obj : Any
        Object to traverse.

    default: Any, optional
        Default value if key was invalid.
        Defaults to None.


    Returns
    -------
    Value stored under specified key or default value.
    """
    if isinstance(path, str):
        path = path.split(".")

    value = obj

    # try to traverse down the sequence of keys defined
    # in the path, to get the target value if it exists
    try:
        for key in path:
            if isinstance(value, list):
                key = int(key)
            value = value[key]
    except (KeyError, TypeError, IndexError):
        value = default

    return value
