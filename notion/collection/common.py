from copy import deepcopy


def _normalize_prop_name(prop_name, collection):
    if not prop_name:
        return ""

    return collection.get_schema_property(prop_name).get("id", "")


def _normalize_query_data(data, collection, recursive=False):
    if not recursive:
        data = deepcopy(data)

    if isinstance(data, list):
        return [
            _normalize_query_data(item, collection, recursive=True) for item in data
        ]

    if isinstance(data, dict):
        # convert slugs to property ids
        if "property" in data:
            data["property"] = _normalize_prop_name(data["property"], collection)

        # convert any instantiated objects into their ids
        if "value" in data and hasattr(data["value"], "id"):
            data["value"] = data["value"].id

        for key in data:
            data[key] = _normalize_query_data(data[key], collection, recursive=True)

    return data
