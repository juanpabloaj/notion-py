from notion.utils import now


def build_operation(
    block_id: str,
    path: str,
    args: dict,
    command: str,
    table: str = "block",
) -> dict:
    """
    Build sequence of operations for submitTransaction endpoint.


    Arguments
    ---------
    block_id : str
        ID of the object.

    path : str
        Key for the object.

    args : dict
        Arguments.

    command : str
        Command to execute.

    table : str, optional
        Table argument for endpoint.
        Defaults to "block".


    Returns
    -------
    dict
        Valid dict for the endpoint.
    """

    def maybe_to_int(value):
        try:
            return int(value)
        except ValueError:
            return value

    path = list(map(maybe_to_int, path.split(".")))
    path = [] if path == [""] else path

    return {
        "id": block_id,
        "path": path,
        "args": args,
        "command": command,
        "table": table,
    }


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
    return build_operation(
        block_id=block_id,
        path="",
        args={"last_edited_by": user_id, "last_edited_time": now()},
        command="update",
    )
