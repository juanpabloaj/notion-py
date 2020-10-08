from copy import deepcopy

from notion.maps import (
    property_map,
    plaintext_property_map,
    field_map,
    prefixed_field_map,
    nested_field_map,
    boolean_property_map,
    Mapper,
)
from notion.record import Record
from notion.settings import BASE_URL
from notion.utils import get_by_path


class Block(Record):
    """
    Base class for every kind of notion block object.

    Most data in Notion is stored as a "block". That includes pages
    and all the individual elements within a page. These blocks have
    different types, and in some cases we create subclasses of this
    class to represent those types.

    Attributes on the `Block` are mapped to useful attributes of the
    server-side data structure, as properties, so you can get and set
    values on the API just by reading/writing attributes on these classes.

    We store a shared local cache on the `NotionClient` object
    of all block data, and reference that as needed from here.
    Data can be refreshed from the server using the `refresh` method.
    """

    _table = "block"
    _type = "block"
    _str_fields = "type"

    # we'll mark it as an alias if we load the Block
    # as a child of a page that is not its parent
    _alias_parent = None
    _child_list_key = "content"

    type = field_map("type")
    alive = field_map("alive")

    def _convert_diff_to_changelist(self, difference, old_val, new_val):
        # TODO: cached property?
        mappers = {}
        for name in dir(self.__class__):
            field = getattr(self.__class__, name)
            if isinstance(field, Mapper):
                mappers[name] = field

        changed_fields = set()
        changes = []
        remaining = []
        content_changed = False

        for d in deepcopy(difference):
            operation, path, values = d

            # normalize path
            path = path if path else []
            path = path.split(".") if isinstance(path, str) else path
            if operation in ["add", "remove"]:
                path.append(values[0][0])
            while isinstance(path[-1], int):
                path.pop()
            path = ".".join(map(str, path))

            # check whether it was content that changed
            if path == "content":
                content_changed = True
                continue

            # check whether the value changed matches
            # one of our mapped fields/properties
            fields = [
                (name, field)
                for name, field in mappers.items()
                if path.startswith(field.path)
            ]
            if fields:
                changed_fields.add(fields[0])
                continue

            remaining.append(d)

        if content_changed:
            old = deepcopy(old_val.get("content", []))
            new = deepcopy(new_val.get("content", []))

            # track what's been added and removed
            removed = set(old) - set(new)
            added = set(new) - set(old)
            for i in removed:
                changes.append(("content_removed", "content", i))
            for i in added:
                changes.append(("content_added", "content", i))

            # ignore the added/removed items, and see whether order has changed
            for i in removed:
                old.remove(i)
            for i in added:
                new.remove(i)
            if old != new:
                changes.append(("content_reordered", "content", (old, new)))

        for name, field in changed_fields:
            old = field.api_to_python(get_by_path(field.path, old_val))
            new = field.api_to_python(get_by_path(field.path, new_val))
            changes.append(("changed_field", name, (old, new)))

        return changes + super()._convert_diff_to_changelist(
            remaining, old_val, new_val
        )

    def get_browseable_url(self) -> str:
        """
        Return direct URL to given Block.


        Returns
        -------
        str
            valid URL
        """
        short_id = self.id.replace("-", "")

        if "page" in self._type:
            return BASE_URL + short_id
        else:
            return self.parent.get_browseable_url() + "#" + short_id

    def remove(self, permanently: bool = False):
        """
        Remove the node from its parent, and mark it as inactive.

        This corresponds to what happens in the Notion UI when you
        delete a block. Note that it doesn't *actually* delete it,
        just orphan it, unless `permanently` is set to True,
        in which case we make an extra call to hard-delete.


        Arguments
        ---------
        permanently : bool, optional
            Whether or not to hard-delete the block.
            Defaults to False.
        """
        if self.is_alias:
            # only remove it from the alias parent's content list
            return self._client.build_and_submit_transaction(
                record_id=self._alias_parent,
                path="content",
                args={"id": self.id},
                command="listRemove",
            )

        with self._client.as_atomic_transaction():
            # Mark the block as inactive
            self._client.build_and_submit_transaction(
                record_id=self.id, path="", args={"alive": False}, command="update"
            )

            # Remove the block's ID from a list on its parent, if needed
            if self.parent._child_list_key:
                self._client.build_and_submit_transaction(
                    record_id=self.parent.id,
                    path=self.parent._child_list_key,
                    args={"id": self.id},
                    command="listRemove",
                    table=self.parent._table,
                )

        if permanently:
            data = {"blockIds": [self.id], "permanentlyDelete": True}
            self._client.post("deleteBlocks", data=data)
            del self._client._store._values["block"][self.id]

    def move_to(self, target_block: "Block", position="last-child"):
        if position not in ["first-child", "last-child", "before", "after"]:
            raise ValueError("Provided value for position is not valid.")

        if "child" in position:
            new_parent_id = target_block.id
            new_parent_table = "block"
        else:
            new_parent_id = target_block.get("parent_id")
            new_parent_table = target_block.get("parent_table")

        if position in ["first-child", "before"]:
            list_command = "listBefore"
        else:
            list_command = "listAfter"

        args = {"id": self.id}
        if position in ["before", "after"]:
            args[position] = target_block.id

        with self._client.as_atomic_transaction():
            # First, remove the node, before we re-insert
            # and re-activate it at the target location
            self.remove()

            if not self.is_alias:
                # Set the parent_id of the moving block to the new parent,
                # and mark it as active again
                self._client.build_and_submit_transaction(
                    record_id=self.id,
                    path="",
                    args={
                        "alive": True,
                        "parent_id": new_parent_id,
                        "parent_table": new_parent_table,
                    },
                    command="update",
                )
            else:
                self._alias_parent = new_parent_id

            # Add the moving block's ID to the "content" list of the new parent
            self._client.build_and_submit_transaction(
                record_id=new_parent_id,
                path="content",
                args=args,
                command=list_command,
            )

        # update the local block cache to reflect the updates
        self._client.refresh_records(
            block=[
                self.id,
                self.get("parent_id"),
                target_block.id,
                target_block.get("parent_id"),
            ]
        )

    def change_lock(self, locked: bool):
        """
        Set or free the lock according to the value passed in `locked`.


        Arguments
        ---------
        locked : bool
            Whether or not to lock the block.
        """
        user_id = self._client.current_user.id
        args = {"block_locked": locked, "block_locked_by": user_id}

        with self._client.as_atomic_transaction():
            self._client.build_and_submit_transaction(
                record_id=self.id,
                path="format",
                args=args,
                command="update",
            )

        # update the local block cache to reflect the updates
        self._client.refresh_records(block=[self.id])

    @property
    def children(self):
        """
        Get block children.


        Returns
        -------
        Children
            Children of this block.
        """
        if not self._children:
            children_ids = self.get("content", [])
            self._client.refresh_records(block=children_ids)
            # TODO: can we do something about that without breaking
            #       the current code layout?
            from notion.block.children import Children

            self._children = Children(parent=self)
        return self._children

    @property
    def is_alias(self):
        return self._alias_parent is not None

    @property
    def parent(self):
        parent_id = self._alias_parent
        parent_table = "block"

        if not self.is_alias:
            parent_id = self.get("parent_id")
            parent_table = self.get("parent_table")

        getter = getattr(self._client, f"get_{parent_table}")
        if getter:
            return getter(parent_id)

        return None


class BasicBlock(Block):

    _type = "block"
    _str_fields = "title"

    title = property_map("title")
    title_plaintext = plaintext_property_map("title")
    color = field_map("format.block_color")


class DividerBlock(Block):

    _type = "divider"


class ColumnBlock(Block):
    """
    Should be added as children of a ColumnListBlock.
    """

    _type = "column"

    column_ratio = field_map("format.column_ratio")


class ColumnListBlock(Block):
    """
    Must contain only ColumnBlocks as children.
    """

    _type = "column_list"

    def evenly_space_columns(self):
        with self._client.as_atomic_transaction():
            for child in self.children:
                child.column_ratio = 1 / len(self.children)


class PageBlock(BasicBlock):

    _type = "page"

    icon = prefixed_field_map("format.page_icon")
    cover = prefixed_field_map("format.page_cover")


class TextBlock(BasicBlock):

    _type = "text"


class CalloutBlock(BasicBlock):

    _type = "callout"

    icon = field_map("format.page_icon")


class CodeBlock(BasicBlock):

    _type = "code"

    language = property_map("language")
    wrap = field_map("format.code_wrap")


class LinkToPageBlock(BasicBlock):

    _type = "link_to_page"


class EquationBlock(BasicBlock):

    _type = "equation"

    latex = nested_field_map("properties.title")


class QuoteBlock(BasicBlock):

    _type = "quote"


class ToDoBlock(BasicBlock):

    _type = "to_do"
    _str_fields = "checked"

    checked = boolean_property_map("checked")


class ToggleBlock(BasicBlock):

    _type = "toggle"


class HeaderBlock(BasicBlock):

    _type = "header"


class SubHeaderBlock(BasicBlock):

    _type = "sub_header"


class SubSubHeaderBlock(BasicBlock):

    _type = "sub_sub_header"


class BulletedListBlock(BasicBlock):

    _type = "bulleted_list"


class NumberedListBlock(BasicBlock):

    _type = "numbered_list"


class FactoryBlock(BasicBlock):
    """
    Also known as a "Template Button"

    The title is the button text,
    and the children are the templates to clone.
    """

    _type = "factory"
