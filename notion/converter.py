from datetime import datetime, date
from random import choice
from typing import Any, Callable
from uuid import uuid1

from notion.block.collection.common import NotionDate
from notion.markdown import markdown_to_notion, notion_to_markdown
from notion.utils import (
    remove_signed_prefix_as_needed,
    add_signed_prefix_as_needed,
    to_list,
    extract_id,
)


class BaseConverter:
    """
    Base Converter.
    """

    _converters = None

    @classmethod
    def _ensure_type(cls, name: str, value, types):
        types = to_list(types)

        for t in types:
            if isinstance(value, t):
                break
        else:
            types = [t.__name__ for t in types]
            msg = f"Value type passed to prop '{name}' must be one of {types}."
            raise TypeError(msg)

    @classmethod
    def _get_converter_for_type(cls, type_: str) -> Callable:
        if not cls._converters:
            cls._converters = [m for m in dir(cls) if m.startswith("convert_")]

        method_name = f"convert_{type_}"
        if method_name in cls._converters:
            return getattr(cls, method_name)

    @classmethod
    def convert(cls, name: str, value: Any, prop: dict, block) -> (str, Any):
        """
        Convert `value` from attribute `name`.


        Attributes
        ----------
        name : str
            Property name.

        value : Any
            Value to convert.

        prop : dict
            More information about the block property.

        block : Block
            instance of the block itself.


        Returns
        -------
        (str, Any)
            Tuple containing property path and converted value.

        """
        prop_id = prop["id"]
        prop_type = prop["type"]
        callback = cls._get_converter_for_type(prop_type)

        if not callback:
            raise ValueError(
                f"Prop '{name}' with type '{prop_type}'"
                " does not have a converter method"
            )

        value = callback(name=name, value=value, prop=prop, block=block)
        return f"properties.{prop_id}", value


class PythonToNotionConverter(BaseConverter):
    @classmethod
    def convert_title(cls, name, value, **_):
        cls._ensure_type(name, value, str)
        return markdown_to_notion(value)

    @classmethod
    def convert_text(cls, **kwargs):
        return cls.convert_title(**kwargs)

    @classmethod
    def convert_number(cls, name, value, **_):
        if value is None:
            return None

        cls._ensure_type(name, value, [int, float])
        return [[str(value)]]

    @classmethod
    def convert_select(cls, value, prop, block, **_):
        value = to_list(value)
        if value == [None]:
            return value

        options = prop["options"] = prop.get("options", [])
        valid_options = [[p["value"].lower() for p in options]]
        colors = [
            "default",
            "gray",
            "brown",
            "orange",
            "yellow",
            "green",
            "blue",
            "purple",
            "pink",
            "red",
        ]

        schema_needs_update = False
        for i, v in enumerate(value):
            value[i] = v = v.replace(",", "")
            v_key = v.lower()

            if v_key not in valid_options:
                schema_needs_update = True
                valid_options.append(v_key)
                options.append(
                    {"id": str(uuid1()), "value": v, "color": choice(colors)}
                )

        value = [[",".join(value)]]

        if schema_needs_update:
            schema = block.collection.get("schema")
            schema[prop["id"]] = prop
            block.collection.set("schema", schema)

        return value

    @classmethod
    def convert_multi_select(cls, **kwargs):
        return cls.convert_select(**kwargs)

    @classmethod
    def convert_email(cls, value, **_):
        return [[value, [["a", value]]]]

    @classmethod
    def convert_phone_number(cls, **kwargs):
        return cls.convert_email(**kwargs)

    @classmethod
    def convert_url(cls, **kwargs):
        return cls.convert_email(**kwargs)

    @classmethod
    def convert_date(cls, name, value, **_):
        cls._ensure_type(name, value, [date, datetime, NotionDate])

        if isinstance(value, NotionDate):
            return value.to_notion()

        return NotionDate(value)

    @classmethod
    def convert_checkbox(cls, name, value, **_):
        cls._ensure_type(name, value, bool)
        return [["Yes" if value else "No"]]

    @classmethod
    def convert_person(cls, value, **_):
        users = []

        for user in to_list(value):
            users += [["‣", [["u", extract_id(user)]]], [","]]

        return users[:-1]

    @classmethod
    def convert_file(cls, value, **_):
        files = []

        for url in to_list(value):
            url = remove_signed_prefix_as_needed(url)
            name = url.split("/")[-1]
            files += [[name, [["a", url]]], [","]]

        return files[:-1]

    @classmethod
    def convert_relation(cls, value, block, **_):
        pages = []

        for page in to_list(value):
            if isinstance(page, str):
                page = block._client.get_block(page)
            pages += [["‣", [["p", page.id]]], [","]]

        return pages[:-1]

    @classmethod
    def convert_created_time(cls, value, **_):
        return int(value.timestamp() * 1000)

    @classmethod
    def convert_last_edited_time(cls, **kwargs):
        return cls.convert_created_time(**kwargs)

    @classmethod
    def convert_created_by(cls, value, **_):
        return extract_id(value)

    @classmethod
    def convert_last_edited_by(cls, **kwargs):
        return cls.convert_created_by(**kwargs)


class NotionToPythonConverter(BaseConverter):
    @classmethod
    def convert_title(cls, value, block, **_):
        for i, part in enumerate(value):
            if len(part) == 2:
                for fmt in part[1]:
                    if "p" in fmt:
                        page = block._client.get_block(fmt[1])
                        title = f"{page.icon} {page.title}"
                        address = page.get_browseable_url()
                        value[i] = f"[{title}]({address})"

        return notion_to_markdown(value) if value else ""

    @classmethod
    def convert_text(cls, **kwargs):
        return cls.convert_title(**kwargs)

    @classmethod
    def convert_number(cls, value, **_):
        if value is None:
            return None

        value = value[0][0].replace(",", "")
        if "." in value:
            return float(value)

        return int(value)

    @classmethod
    def convert_select(cls, value, **_):
        return value[0][0] if value else None

    @classmethod
    def convert_multi_select(cls, value, **_):
        if not value:
            return []

        return [v.strip() for v in value[0][0].split(",")]

    @classmethod
    def convert_email(cls, **kwargs):
        return cls.convert_select(**kwargs)

    @classmethod
    def convert_phone_number(cls, **kwargs):
        return cls.convert_select(**kwargs)

    @classmethod
    def convert_url(cls, **kwargs):
        return cls.convert_select(**kwargs)

    @classmethod
    def convert_date(cls, value, **_):
        return NotionDate.from_notion(value)

    @classmethod
    def convert_checkbox(cls, value, **_):
        return value[0][0] == "Yes" if value else False

    @classmethod
    def convert_person(cls, value, block, **_):
        if not value:
            return []

        items = [i[1][0][1] for i in value if i[0] == "‣"]
        return [block._client.get_user(i) for i in items]

    @classmethod
    def convert_file(cls, value, block, **_):
        if not value:
            return []

        client = block._client
        items = [i[1][0][1] for i in value if i[0] != ","]
        return [add_signed_prefix_as_needed(i, client=client) for i in items]

    @classmethod
    def convert_relation(cls, value, block, **_):
        if not value:
            return []

        items = [i[1][0][1] for i in value if i[0] != "‣"]
        return [block._client.get_block(i) for i in items]

    @classmethod
    def convert_created_time(cls, block, prop, **_):
        value = block.get(prop["type"])
        value = datetime.utcfromtimestamp(value / 1000)
        return int(value.timestamp() * 1000)

    @classmethod
    def convert_last_edited_time(cls, **kwargs):
        return cls.convert_created_time(**kwargs)

    @classmethod
    def convert_created_by(cls, block, prop, **_):
        value = block.get(prop["type"] + "_id")
        return block._client.get_user(value)

    @classmethod
    def convert_last_edited_by(cls, **kwargs):
        return cls.convert_created_by(**kwargs)
