from datetime import datetime
from functools import cached_property
from typing import Any

from notion.block.basic import PageBlock
from notion.markdown import notion_to_markdown, markdown_to_notion
from notion.operations import build_operation
from notion.utils import (
    slugify,
    add_signed_prefix_as_needed,
    remove_signed_prefix_as_needed,
)


class CollectionBlock(PageBlock):
    """
    Collection Row Block.
    """

    _type = "collection"

    def __dir__(self):
        # TODO: what's that about?
        # return self._get_property_slugs() + super().__dir__()
        return self._get_property_slugs()

    def __getattr__(self, attname):
        return self.get_property(attname)

    def __setattr__(self, name: str, value: Any):
        if name.startswith("_") or hasattr(self, name):
            # we only allow setting of new non-property attributes that start with "_"
            super().__setattr__(name, value)

        elif slugify(name) in self._get_property_slugs():
            self.set_property(slugify(name), value)

        else:
            raise AttributeError(f"Unknown property: '{name}'")

    def _get_property_slugs(self) -> list:
        """

        Returns
        -------
        list
            List of slugs.
        """
        slugs = [prop["slug"] for prop in self.schema]
        if "title" not in slugs:
            slugs.append("title")
        return slugs

    def _convert_diff_to_changelist(self, difference, old_val, new_val):

        changed_props = set()
        changes = []
        remaining = []

        for d in difference:
            operation, path, values = d
            path = path.split(".") if isinstance(path, str) else path
            if path and path[0] == "properties":
                if len(path) > 1:
                    changed_props.add(path[1])
                else:
                    for item in values:
                        changed_props.add(item[0])
            else:
                remaining.append(d)

        for prop_id in changed_props:
            prop = self.collection.get_schema_property(prop_id)
            old = self._convert_notion_to_python(
                old_val.get("properties", {}).get(prop_id), prop
            )
            new = self._convert_notion_to_python(
                new_val.get("properties", {}).get(prop_id), prop
            )
            changes.append(("prop_changed", prop["slug"], (old, new)))

        return changes + super()._convert_diff_to_changelist(
            remaining, old_val, new_val
        )

    def _convert_mentioned_pages_to_python(self, val, prop):
        if not prop["type"] in ["title", "text"]:
            raise TypeError(
                "The property must be an title or text to convert mentioned pages to Python."
            )

        pages = []
        for i, part in enumerate(val):
            if len(part) == 2:
                for format in part[1]:
                    if "p" in format:
                        pages.append(self._client.get_block(format[1]))

        return pages

    def _convert_notion_to_python(self, val, prop: dict):
        if prop["type"] in ["title", "text"]:
            for i, part in enumerate(val):
                if len(part) == 2:
                    for format in part[1]:
                        if "p" in format:
                            page = self._client.get_block(format[1])
                            link = f"[{page.icon} {page.title}]({page.get_browseable_url()})"
                            val[i] = [link]

            val = notion_to_markdown(val) if val else ""
        if prop["type"] in ["number"]:
            if val is not None:
                val = val[0][0]
                if "." in val:
                    val = float(val)
                else:
                    val = int(val)
        if prop["type"] in ["select"]:
            val = val[0][0] if val else None
        if prop["type"] in ["multi_select"]:
            val = [v.strip() for v in val[0][0].split(",")] if val else []
        if prop["type"] in ["person"]:
            val = (
                [self._client.get_user(item[1][0][1]) for item in val if item[0] == "‣"]
                if val
                else []
            )
        if prop["type"] in ["email", "phone_number", "url"]:
            val = val[0][0] if val else ""
        # TODO: fix this case, NotionDate does not exist
        # if prop["type"] in ["date"]:
        #     val = NotionDate.from_notion(val)
        if prop["type"] in ["file"]:
            val = (
                [
                    add_signed_prefix_as_needed(item[1][0][1], client=self._client)
                    for item in val
                    if item[0] != ","
                ]
                if val
                else []
            )
        if prop["type"] in ["checkbox"]:
            val = val[0][0] == "Yes" if val else False
        if prop["type"] in ["relation"]:
            val = (
                [
                    self._client.get_block(item[1][0][1])
                    for item in val
                    if item[0] == "‣"
                ]
                if val
                else []
            )
        if prop["type"] in ["created_time", "last_edited_time"]:
            val = self.get(prop["type"])
            val = datetime.utcfromtimestamp(val / 1000)
        if prop["type"] in ["created_by", "last_edited_by"]:
            val = self.get(prop["type"])
            val = self._client.get_user(val)

        return val

    def _convert_python_to_notion(self, val, prop, identifier="<unknown>"):

        if prop["type"] in ["title", "text"]:
            if not val:
                val = ""
            if not isinstance(val, str):
                raise TypeError(
                    "Value passed to property '{}' must be a string.".format(identifier)
                )
            val = markdown_to_notion(val)
        if prop["type"] in ["number"]:
            if val is not None:
                if not isinstance(val, float) and not isinstance(val, int):
                    raise TypeError(
                        "Value passed to property '{}' must be an int or float.".format(
                            identifier
                        )
                    )
                val = [[str(val)]]
        if prop["type"] in ["select"]:
            if not val:
                val = None
            else:
                valid_options = [p["value"].lower() for p in prop["options"]]
                val = val.split(",")[0]
                if val.lower() not in valid_options:
                    raise ValueError(
                        "Value '{}' not acceptable for property '{}' (valid options: {})".format(
                            val, identifier, valid_options
                        )
                    )
                val = [[val]]
        if prop["type"] in ["multi_select"]:
            if not val:
                val = []
            valid_options = [p["value"].lower() for p in prop["options"]]
            if not isinstance(val, list):
                val = [val]
            for v in val:
                if v.lower() not in valid_options:
                    raise ValueError(
                        "Value '{}' not acceptable for property '{}' (valid options: {})".format(
                            v, identifier, valid_options
                        )
                    )
            val = [[",".join(val)]]
        if prop["type"] in ["person"]:
            userlist = []
            if not isinstance(val, list):
                val = [val]
            for user in val:
                user_id = user if isinstance(user, str) else user.id
                userlist += [["‣", [["u", user_id]]], [","]]
            val = userlist[:-1]
        if prop["type"] in ["email", "phone_number", "url"]:
            val = [[val, [["a", val]]]]
        # if prop["type"] in ["date"]:
        #     if isinstance(val, date) or isinstance(val, datetime):
        #         val = NotionDate(val)
        #     if isinstance(val, NotionDate):
        #         val = val.to_notion()
        #     else:
        #         val = []
        if prop["type"] in ["file"]:
            filelist = []
            if not isinstance(val, list):
                val = [val]
            for url in val:
                url = remove_signed_prefix_as_needed(url)
                filename = url.split("/")[-1]
                filelist += [[filename, [["a", url]]], [","]]
            val = filelist[:-1]
        if prop["type"] in ["checkbox"]:
            if not isinstance(val, bool):
                raise TypeError(
                    "Value passed to property '{}' must be a bool.".format(identifier)
                )
            val = [["Yes" if val else "No"]]
        if prop["type"] in ["relation"]:
            pagelist = []
            if not isinstance(val, list):
                val = [val]
            for page in val:
                if isinstance(page, str):
                    page = self._client.get_block(page)
                pagelist += [["‣", [["p", page.id]]], [","]]
            val = pagelist[:-1]
        if prop["type"] in ["created_time", "last_edited_time"]:
            val = int(val.timestamp() * 1000)
            return prop["type"], val
        if prop["type"] in ["created_by", "last_edited_by"]:
            val = val if isinstance(val, str) else val.id
            return prop["type"], val

        return ["properties", prop["id"]], val

    def get_all_properties(self):
        allprops = {}
        for prop in self.schema:
            propid = slugify(prop["name"])
            allprops[propid] = self.get_property(propid)
        return allprops

    def get_property(self, identifier):

        prop = self.collection.get_schema_property(identifier)
        if prop is None:
            raise AttributeError(
                "Object does not have property '{}'".format(identifier)
            )

        val = self.get(["properties", prop["id"]])

        return self._convert_notion_to_python(val, prop)

    def get_mentioned_pages_on_property(self, identifier):
        prop = self.collection.get_schema_property(identifier)
        if prop is None:
            raise AttributeError(
                "Object does not have property '{}'".format(identifier)
            )
        val = self.get(["properties", prop["id"]])
        return self._convert_mentioned_pages_to_python(val, prop)

    def set_property(self, identifier, val):

        prop = self.collection.get_schema_property(identifier)
        if prop is None:
            raise AttributeError(
                "Object does not have property '{}'".format(identifier)
            )

        path, val = self._convert_python_to_notion(val, prop, identifier=identifier)

        self.set(path, val)

    def remove(self):
        # Mark the block as inactive
        self._client.submit_transaction(
            build_operation(
                id=self.id, path=[], args={"alive": False}, command="update"
            )
        )

    @property
    def is_template(self):
        return self.get("is_template")

    @cached_property
    def collection(self):
        return self._client.get_collection(self.get("parent_id"))

    @property
    def schema(self):
        return [
            prop
            for prop in self.collection.get_schema_properties()
            if prop["type"] not in ["formula", "rollup"]
        ]


class TemplateBlock(CollectionBlock):
    """
    Template block.

    """

    _type = "template"

    @property
    def is_template(self):
        return self.get("is_template")

    @is_template.setter
    def is_template(self, val):
        if not val:
            raise ValueError("TemplateBlock must have 'is_template' set to True.")

        self.set("is_template", True)
