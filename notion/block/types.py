from importlib import import_module


def _get_blocks(file_name: str, suffix: str = "Block") -> dict:
    """
    Get a mapping of types and classes
    that end with `suffix` found in `file_name`.


    This function caches the results using `file_name` as a key.


    Arguments
    ---------
    file_name : str
        File name to the file in `notion.block` module.
        Pass it without extension (.py).

    suffix : str, optional
        Class suffix to used to filter the objects.
        Defaults to "Block".


    Returns
    -------
    dict
        Mapping of types to their classes.
    """
    cache = getattr(_get_blocks, "_cache", {})

    if cache.get(file_name):
        return cache[file_name]

    module = import_module(f"notion.block.{file_name}")
    blocks = {}

    for name in dir(module):
        if name.endswith(suffix):
            klass = getattr(module, name)
            blocks[klass._type] = klass

    cache[file_name] = blocks
    setattr(_get_blocks, "_cache", cache)

    return blocks


def get_all_block_types() -> dict:
    return {
        **_get_blocks("basic"),
        **_get_blocks("database"),
        **_get_blocks("embed"),
        **_get_blocks("inline"),
        **_get_blocks("media"),
        **_get_blocks("upload"),
        **_get_blocks("collection.basic"),
        **_get_blocks("collection.media"),
    }


def get_block_type(block_type: str = "", default="block"):
    blocks = get_all_block_types()
    return blocks.get(block_type, None) or blocks[default]


def get_collection_view_type(view_type: str, default="collection_view"):
    blocks = _get_blocks("collection.view", "View")
    return blocks.get(view_type, None) or blocks[default]


def get_collection_query_result_type(query_result_type: str, default="collection"):
    blocks = _get_blocks("collection.query", "QueryResult")
    return blocks.get(query_result_type, None) or blocks[default]
