from notion.block.common import Templates
from notion.block.collection import CollectionBlock
from notion.collection.query import CollectionQuery
from notion.collection.view import CalendarView
from notion.maps import field_map, markdown_field_map
from notion.record import Record
from notion.utils import slugify


class Collection(Record):
    """
    A "collection" corresponds to what's called a "database" in the Notion UI.
    """

    name = markdown_field_map("name")
    description = markdown_field_map("description")
    cover = field_map("cover")

    @property
    def templates(self):
        if not hasattr(self, "_templates"):
            template_ids = self.get("template_pages", [])
            self._client.refresh_records(block=template_ids)
            self._templates = Templates(parent=self)
        return self._templates

    def get_schema_properties(self):
        """
        Fetch a flattened list of all properties in the collection's schema.
        """
        properties = []
        schema = self.get("schema")
        for id, item in schema.items():
            prop = {"id": id, "slug": slugify(item["name"])}
            prop.update(item)
            properties.append(prop)
        return properties

    def get_schema_property(self, identifier):
        """
        Look up a property in the collection's schema, by "property id" (generally a 4-char string),
        or name (human-readable -- there may be duplicates, so we pick the first match we find).
        """
        for prop in self.get_schema_properties():
            if identifier == prop["id"] or slugify(identifier) == prop["slug"]:
                return prop
            if identifier == "title" and prop["type"] == "title":
                return prop
        return None

    def add_row(self, update_views=True, **kwargs):
        """
        Create a new empty CollectionBlock under this collection, and return the instance.
        """

        row_id = self._client.create_record("block", self, type="page")
        row = CollectionBlock(self._client, row_id)

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
        assert self.get("parent_table") == "block"
        return self._client.get_block(self.get("parent_id"))

    def _get_a_collection_view(self):
        """
        Get an arbitrary collection view for this collection, to allow querying.
        """
        return self.parent.views[0]

    def query(self, **kwargs):
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
