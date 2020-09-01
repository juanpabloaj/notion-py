from typing import Union, Iterable

from notion.utils import now


def build_operation(
    id: str,
    path: Union[Iterable, str],
    args,
    command: str = "set",
    table: str = "block",
) -> dict:
    """
    Build sequence of operations for submitTransaction endpoint.


    Arguments
    ---------
    id : str
        ID of the object.

    path : list of str or str
        Key for the object.


    args
        Arguments?

    command : str, optional
        Command to execute.
        Defaults to "set".

    table : str, optional
        Table argument for endpoint.
        Defaults to "block".


    Returns
    -------
    dict
        Valid dict for the endpoint.
    """
    if isinstance(path, str):
        path = path.split(".")

    return {"id": id, "path": path, "args": args, "command": command, "table": table}


def operation_update_last_edited(user_id, block_id) -> dict:
    """
    Convenience function for constructing "last edited" operation.

    When transactions are submitted from the web UIit also
    includes an operation to update the "last edited" fields,
    so we want to send those too, for consistency.


    Arguments
    ---------
    user_id : str
        User ID

    block_id : str
        Block ID


    Returns
    -------
    dict
        Constructed dict with last edited operation included.
    """
    return {
        "args": {"last_edited_by": user_id, "last_edited_time": now()},
        "command": "update",
        "id": block_id,
        "path": [],
        "table": "block",
    }
