from inspect import signature
from typing import Callable

from notion.markdown import (
    markdown_to_notion,
    notion_to_markdown,
    plaintext_to_notion,
    notion_to_plaintext,
)
from notion.utils import (
    add_signed_prefix_as_needed,
    remove_signed_prefix_as_needed,
)


class Mapper(property):
    """
    Mapper for converting to/from notion and Python.
    """

    def __init__(
        self,
        path: str,
        python_to_api: Callable,
        api_to_python: Callable,
        *args,
        **kwargs,
    ):
        """
        Create mapper object and fill its fields.


        Arguments
        ---------
        path : str
            Path can either be a top-level field-name or a
            dot-delimited string representing the key names to traverse.

        python_to_api : Callable
            Function that converts values as given in the Python layer
            into the internal API representation.

        api_to_python : Callable
            Function that converts what is received from the API
            into an internal representation to be returned to the Python layer.
        """
        self.path = path
        self.python_to_api = python_to_api
        self.api_to_python = api_to_python
        super().__init__(*args, **kwargs)


def field_map(
    path: str,
    python_to_api: Callable = lambda x: x,
    api_to_python: Callable = lambda x: x,
) -> Mapper:
    """
    Return a property that maps a Block attribute
    onto a field in the API data structures.


    Arguments
    ---------
    path : str
        Path can either be a top-level field-name or a
        dot-delimited string representing the key names to traverse.

    python_to_api : Callable, optional
        Function that converts values as given in the Python layer into
        the internal API representation.
        Defaults to proxy lambda x: x.

    api_to_python : Callable, optional
        Function that converts what is received from the API into
        an internal representation to be returned to the Python layer.
        Defaults to proxy lambda x: x.


    Returns
    -------
    Mapper
        Property map.


    See Also
    --------
    property_map
    """

    def fget(self):
        kwargs = {}
        if "client" in signature(api_to_python).parameters:
            kwargs["client"] = self._client

        return api_to_python(self.get(path), **kwargs)

    def fset(self, value):
        kwargs = {}
        if "client" in signature(python_to_api).parameters:
            kwargs["client"] = self._client

        self.set(path, python_to_api(value, **kwargs))

    return Mapper(
        path=path,
        python_to_api=python_to_api,
        api_to_python=api_to_python,
        fget=fget,
        fset=fset,
    )


def prefixed_field_map(name: str) -> Mapper:
    """
    Arguments
    ---------
    name : str
        Name of the property.


    Returns
    -------
    Mapper
        Field map.


    See Also
    --------
    field_map
    """
    return field_map(
        name,
        api_to_python=add_signed_prefix_as_needed,
        python_to_api=remove_signed_prefix_as_needed,
    )


def nested_field_map(name: str) -> Mapper:
    """
    Arguments
    ---------
    name : str
        Name of the property.


    Returns
    -------
    Mapper
        Field map.


    See Also
    --------
    field_map
    """
    return field_map(
        name,
        python_to_api=lambda x: [[x]],
        api_to_python=lambda x: x[0][0],
    )


def markdown_field_map(name: str) -> Mapper:
    """
    Arguments
    ---------
    name : str
        Name of the property.


    Returns
    -------
    Mapper
        Field map.


    See Also
    --------
    field_map
    """
    return field_map(
        name, api_to_python=notion_to_markdown, python_to_api=markdown_to_notion
    )


def property_map(
    name: str,
    python_to_api: Callable = lambda x: x,
    api_to_python: Callable = lambda x: x,
    markdown: bool = True,
) -> Mapper:
    """
    Similar to `field_map`, except it works specifically with
    the data under the "properties" field in the API block table,
    and just takes a single name to specify which subkey to reference.

    Also, these properties all seem to use a special "embedded list"
    format that breaks the text up into a sequence of chunks and associated
    format metadata.


    Arguments
    ---------
    name : str
        Name of the property.

    python_to_api : Callable, optional
        Function that converts values as given in the Python layer into
        the internal API representation.
        Defaults to proxy lambda x: x.

    api_to_python : Callable, optional
        Function that converts what is received from the API into
        an internal representation to be returned to the Python layer.
        Defaults to proxy lambda x: x.

    markdown : bool, optional
        Whether or not to convert the representation into commonmark-compatible
        markdown text upon reading from API and again when saving.
        Defaults to True.


    Returns
    -------
    Mapper
        Property map.


    See Also
    --------
    field_map
    """

    def py2api(x, client=None):
        kwargs = {}
        if "client" in signature(python_to_api).parameters:
            kwargs["client"] = client

        x = python_to_api(x, **kwargs)
        if markdown:
            x = markdown_to_notion(x)

        return x

    def api2py(x, client=None):
        x = x or [[""]]

        if markdown:
            x = notion_to_markdown(x)

        kwargs = {}
        if "client" in signature(api_to_python).parameters:
            kwargs["client"] = client

        return api_to_python(x, **kwargs)

    path = f"properties.{name}"
    return field_map(path, python_to_api=py2api, api_to_python=api2py)


def prefixed_property_map(name: str) -> Mapper:
    """
    Arguments
    ---------
    name : str
        Name of the property.


    Returns
    -------
    Mapper
        Property map.


    See Also
    --------
    property_map
    """
    return property_map(
        name,
        api_to_python=add_signed_prefix_as_needed,
        python_to_api=remove_signed_prefix_as_needed,
    )


def plaintext_property_map(name: str) -> Mapper:
    """
    Arguments
    ---------
    name : str
        Name of the property.


    Returns
    -------
    Mapper
        Property map.


    See Also
    --------
    property_map
    """
    return property_map(
        name,
        python_to_api=plaintext_to_notion,
        api_to_python=notion_to_plaintext,
        markdown=False,
    )


def boolean_property_map(name: str) -> Mapper:
    """
    Arguments
    ---------
    name : str
        Name of the property.


    Returns
    -------
    Mapper
        Property map.


    See Also
    --------
    property_map
    """
    return property_map(
        name,
        python_to_api=lambda x: "Yes" if x else "No",
        api_to_python=lambda x: x == "Yes",
    )
