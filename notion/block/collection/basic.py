from typing import Optional

from notion.block.basic import PageBlock, Block
from notion.block.children import Templates
from notion.block.collection.media import CollectionViewBlock
from notion.block.collection.query import CollectionQuery
from notion.block.collection.view import CalendarView
from notion.converter import PythonToNotionConverter, NotionToPythonConverter
from notion.maps import markdown_field_map, field_map
from notion.utils import (
    slugify,
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

    def _get_a_collection_view(self):
        """
        Get an arbitrary collection view for this collection, to allow querying.
        """
        parent = self.parent
        assert isinstance(parent, CollectionViewBlock)
        assert len(parent.views) > 0
        return parent.views[0]

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
            properties.append({"id": block_id, "slug": slug, **item})

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
        """
        Get all rows from a collection.


        Returns
        -------
        CollectionQueryResult
            All rows.
        """
        return self.query(**kwargs)

    @property
    def templates(self) -> Templates:
        if not self._templates:
            template_pages = self.get("template_pages", [])
            self._client.refresh_records(block=template_pages)
            self._templates = Templates(parent=self)

        return self._templates

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


class CollectionRowBlock(PageBlock):
    """
    Collection Row Block.
    """

    def __getattr__(self, attname):
        return self.get_property(attname)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            # we only allow setting of new non-property
            # attributes that start with "_"
            super().__setattr__(name, value)
            return

        slugs = self._get_property_slugs()
        if name in slugs:
            self.set_property(name, value)
            return

        slugged_name = slugify(name)
        if slugged_name in slugs:
            self.set_property(slugged_name, value)
            return

        if hasattr(self, name):
            super().__setattr__(name, value)
            return

        raise AttributeError(f"Unknown property: '{name}'")

    def __dir__(self):
        return self._get_property_slugs() + dir(super())

    def _get_property_slugs(self):
        slugs = [prop["slug"] for prop in self.schema]
        if "title" not in slugs:
            slugs.append("title")
        return slugs

    def _get_property(self, name):
        prop = self.collection.get_schema_property(name)
        if prop is None:
            raise AttributeError(f"Object does not have property '{name}'")

        prop_id = prop["id"]
        value = self.get(f"properties.{prop_id}")
        return value, prop

    def _convert_diff_to_changelist(self, difference, old_val, new_val):
        changed_props = set()
        changes = []
        remaining = []

        for d in difference:
            operation, path, values = d
            path = path.split(".") if isinstance(path, str) else path
            if path and path[0] == "properties":
                if len(path):
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

    def _convert_mentioned_pages_to_python(self, value, prop):
        if not prop["type"] in ["title", "text"]:
            raise TypeError(
                "The property must be an title or text to convert mentioned pages to Python."
            )

        pages = []
        for i, part in enumerate(value):
            if len(part) == 2:
                for format in part[1]:
                    if "p" in format:
                        pages.append(self._client.get_block(format[1]))

        return pages

    def _convert_notion_to_python(self, val, prop):
        _, value = NotionToPythonConverter.convert(
            name="<unknown>", value=val, prop=prop, block=self
        )
        return value

    def _convert_python_to_notion(self, val, prop, name="<unknown>"):
        return PythonToNotionConverter.convert(
            name=name, value=val, prop=prop, block=self
        )

    def get_property(self, name):
        return self._convert_notion_to_python(*self._get_property(name))

    def get_all_properties(self):
        props = {}
        for prop in self.schema:
            prop_id = slugify(prop["name"])
            props[prop_id] = self.get_property(prop_id)

        return props

    def set_property(self, name, value):
        _, prop = self._get_property(name)
        self.set(*self._convert_python_to_notion(value, prop, name))

    def get_mentioned_pages_on_property(self, name):
        return self._convert_mentioned_pages_to_python(*self._get_property(name))

    @property
    def is_template(self):
        return self.get("is_template")

    @property
    def collection(self):
        return self._client.get_collection(self.get("parent_id"))

    @property
    def schema(self):
        props = self.collection.get_schema_properties()
        return [p for p in props if p["type"] not in ["formula", "rollup"]]


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
