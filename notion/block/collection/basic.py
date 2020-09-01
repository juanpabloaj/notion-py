from datetime import datetime, date
from typing import Optional

from notion.block.basic import PageBlock, Block
from notion.block.children import Templates
from notion.block.collection.common import NotionDate
from notion.block.collection.media import CollectionViewBlock
from notion.block.collection.query import CollectionQuery
from notion.block.collection.view import CalendarView
from notion.maps import markdown_field_map, field_map
from notion.markdown import notion_to_markdown, markdown_to_notion
from notion.operations import build_operation
from notion.utils import (
    slugify,
    add_signed_prefix_as_needed,
    remove_signed_prefix_as_needed,
)


class CollectionBlock(Block):
    """
    Collection Block.
    """

    _type = "collection"
    _table = "collection"
    _str_fields = "name"

    cover = field_map("cover")
    name = markdown_field_map("name")
    description = markdown_field_map("description")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._templates = None

    @property
    def templates(self) -> Templates:
        if not self._templates:
            template_ids = self.get("template_pages", [])
            self._client.refresh_records(block=template_ids)
            self._templates = Templates(parent=self)
        return self._templates

    def get_schema_properties(self) -> list:
        """
        Fetch a flattened list of all properties in the collection's schema.


        Returns
        -------
        list
            All properties.
        """
        properties = []
        for block_id, item in self.get("schema").items():
            slug = slugify(item["name"])
            prop = {"id": block_id, "slug": slug, **item}
            properties.append(prop)

        return properties

    def get_schema_property(self, identifier: str) -> Optional[dict]:
        """
        Look up a property in the collection's schema
        by "property id" (generally a 4-char string),
        or name (human-readable -- there may be duplicates
        so we pick the first match we find).


        Attributes
        ----------
        identifier : str
            Value used for searching the prop.
            Can be set to ID, slug or title (if property type is also title).


        Returns
        -------
        dict, optional
            Schema of the property if found, or None.
        """
        for prop in self.get_schema_properties():
            if identifier == prop["id"] or slugify(identifier) == prop["slug"]:
                return prop
            if identifier == "title" and prop["type"] == "title":
                return prop
        return None

    def add_row(self, update_views=True, **kwargs) -> "CollectionRowBlock":
        """
        Create a new empty CollectionRowBlock
        under this collection, and return the instance.


        Arguments
        ---------
        update_views : bool, optional
            Whether or not to update the views after
            adding the row to Collection.
            Defaults to True.

        kwargs : dict, optional
            Additional pairs of keys and values set in
            newly created CollectionRowBlock.
            Defaults to empty dict()


        Returns
        -------
        CollectionRowBlock
            Added row.
        """

        row_id = self._client.create_record("block", self, type="page")
        row = CollectionRowBlock(self._client, row_id)

        with self._client.as_atomic_transaction():
            for key, val in kwargs.items():
                setattr(row, key, val)
            if update_views:
                # make sure the new record is inserted at the end of each view
                for view in self.parent.views:
                    if isinstance(view, CalendarView):
                        continue
                    view.set("page_sort", view.get("page_sort", []) + [row_id])

        return row

    @property
    def parent(self):
        """
        Get parent block.


        Returns
        -------
        Block
            Parent block.
        """
        assert self.get("parent_table") == "block"
        return self._client.get_block(self.get("parent_id"))

    def _get_a_collection_view(self):
        """
        Get an arbitrary collection view for this collection, to allow querying.
        """
        parent = self.parent
        assert isinstance(parent, CollectionViewBlock)
        assert len(parent.views) > 0
        return parent.views[0]

    def query(self, **kwargs):
        """
        Run a query inline and return the results.


        Returns
        -------
        CollectionQueryResult
            Result of passed query.
        """
        return CollectionQuery(self, self._get_a_collection_view(), **kwargs).execute()

    def get_rows(self, **kwargs):
        return self.query(**kwargs)

    def _convert_diff_to_changelist(self, difference, old_val, new_val):
        changes = []
        remaining = []

        for operation, path, values in difference:
            if path == "rows":
                changes.append((operation, path, values))
            else:
                remaining.append((operation, path, values))

        return changes + super()._convert_diff_to_changelist(
            remaining, old_val, new_val
        )


class CollectionRowBlock(PageBlock):
    """
    Collection Row Block.
    """

    @property
    def is_template(self):
        return self.get("is_template")

    @property
    def collection(self):
        return self._client.get_collection(self.get("parent_id"))

    @property
    def schema(self):
        return [
            prop
            for prop in self.collection.get_schema_properties()
            if prop["type"] not in ["formula", "rollup"]
        ]

    def __getattr__(self, attname):
        return self.get_property(attname)

    def __setattr__(self, attname, value):
        if attname.startswith("_"):
            # we only allow setting of new non-property attributes that start with "_"
            super().__setattr__(attname, value)
        elif attname in self._get_property_slugs():
            self.set_property(attname, value)
        elif slugify(attname) in self._get_property_slugs():
            self.set_property(slugify(attname), value)
        elif hasattr(self, attname):
            super().__setattr__(attname, value)
        else:
            raise AttributeError("Unknown property: '{}'".format(attname))

    def _get_property_slugs(self):
        slugs = [prop["slug"] for prop in self.schema]
        if "title" not in slugs:
            slugs.append("title")
        return slugs

    def __dir__(self):
        return self._get_property_slugs() + dir(super())

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

    def _convert_notion_to_python(self, val, prop):
        # TODO: REWRITE THIS MONSTROSITY !!

        if prop["type"] in ["title", "text"]:
            for i, part in enumerate(val):
                if len(part) == 2:
                    for format in part[1]:
                        if "p" in format:
                            page = self._client.get_block(format[1])
                            val[i] = [
                                "["
                                + page.icon
                                + " "
                                + page.title
                                + "]("
                                + page.get_browseable_url()
                                + ")"
                            ]

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
        if prop["type"] in ["date"]:
            val = NotionDate.from_notion(val)
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

    def get_all_properties(self):
        allprops = {}
        for prop in self.schema:
            propid = slugify(prop["name"])
            allprops[propid] = self.get_property(propid)
        return allprops

    def set_property(self, identifier, val):

        prop = self.collection.get_schema_property(identifier)
        if prop is None:
            raise AttributeError(
                "Object does not have property '{}'".format(identifier)
            )

        path, val = self._convert_python_to_notion(val, prop, identifier=identifier)

        self.set(path, val)

    def _convert_python_to_notion(self, val, prop, identifier="<unknown>"):
        # TODO: rewrite this terrible mess

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
        if prop["type"] in ["date"]:
            if isinstance(val, date) or isinstance(val, datetime):
                val = NotionDate(val)
            if isinstance(val, NotionDate):
                val = val.to_notion()
            else:
                val = []
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

    def remove(self):
        # Mark the block as inactive
        self._client.submit_transaction(
            build_operation(
                id=self.id, path=[], args={"alive": False}, command="update"
            )
        )


class TemplateBlock(CollectionRowBlock):
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
