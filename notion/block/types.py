from importlib import import_module


def get_blocks(file_name: str, suffix: str = "Block") -> dict:
    """
    Get list of classes that end with `suffix` from some `file_name`.

    This function caches the results using `file_name` as a key.


    Arguments
    ---------
    file_name : str
        File name to the file in `notion.block` module. Without extension.

    suffix : str, optional
        Class suffix to used to filter the objects.
        Defaults to "Block".


    Returns
    -------
    dict
        Mapping of types to their classes.
    """
    cache = getattr(get_blocks, "_cache", {})

    if cache.get(file_name):
        return cache[file_name]

    module = import_module(f"notion.block.{file_name}")
    blocks = {}

    for name in dir(module):
        if name.endswith(suffix):
            klass = getattr(module, name)
            blocks[klass._type] = klass

    cache[file_name] = blocks
    setattr(get_blocks, "_cache", cache)

    return blocks


def all_block_types() -> dict:
    return {
        **get_blocks("basic"),
        **get_blocks("database"),
        **get_blocks("embed"),
        **get_blocks("inline"),
        **get_blocks("media"),
        **get_blocks("upload"),
        **get_blocks("collection.basic"),
        **get_blocks("collection.media"),
    }


def collection_view_types() -> dict:
    return get_blocks("collection.view", "View")


def collection_query_result_types() -> dict:
    return get_blocks("collection.query", "QueryResult")
