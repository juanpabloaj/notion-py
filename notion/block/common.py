import time
from copy import deepcopy
from typing import Union

from notion.logger import logger
from notion.maps import field_map, Mapper
from notion.operations import build_operation
from notion.record import Record
from notion.utils import get_by_path, extract_id
from notion.block.types import all_block_types


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

    # TODO: change name of this attr?
    child_list_key = "content"

    type = field_map("type")
    alive = field_map("alive")

    @property
    def children(self):
        if not self._children:
            children_ids = self.get("content", [])
            self._client.refresh_records(block=children_ids)
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

            # check whether the value changed matches one of our mapped fields/properties
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
            for id in removed:
                changes.append(("content_removed", "content", id))
            for id in added:
                changes.append(("content_added", "content", id))

            # ignore the added/removed items, and see whether order has changed
            for id in removed:
                old.remove(id)
            for id in added:
                new.remove(id)
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
        return "NOT IMPLEMENTED"

    #        """
    #        Return direct URL to given Block.
    #
    #        Returns
    #        -------
    #        str
    #            valid URL
    #        """
    #        if "page" in self._type:
    #            return BASE_URL + self.id.replace("-", "")
    #        else:
    #            return self.parent.get_browseable_url() + "#" + self.id.replace("-", "")

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
            return self._client.submit_transaction(
                build_operation(
                    id=self._alias_parent,
                    path="content",
                    args={"id": self.id},
                    command="listRemove",
                )
            )

        with self._client.as_atomic_transaction():
            # Mark the block as inactive
            self._client.submit_transaction(
                build_operation(
                    id=self.id, path=[], args={"alive": False}, command="update"
                )
            )

            # Remove the block's ID from a list on its parent, if needed
            if self.parent.child_list_key:
                self._client.submit_transaction(
                    build_operation(
                        id=self.parent.id,
                        path=[self.parent.child_list_key],
                        args={"id": self.id},
                        command="listRemove",
                        table=self.parent._table,
                    )
                )

        if permanently:
            self._client.post(
                "deleteBlocks", {"blockIds": [self.id], "permanentlyDelete": True}
            )
            del self._client._store._values["block"][self.id]


#    def move_to(self, target_block, position="last-child"):
#        assert isinstance(
#            target_block, Block
#        ), "target_block must be an instance of Block or one of its subclasses"
#        assert position in ["first-child", "last-child", "before", "after"]
#
#        if "child" in position:
#            new_parent_id = target_block.id
#            new_parent_table = "block"
#        else:
#            new_parent_id = target_block.get("parent_id")
#            new_parent_table = target_block.get("parent_table")
#
#        if position in ["first-child", "before"]:
#            list_command = "listBefore"
#        else:
#            list_command = "listAfter"
#
#        list_args = {"id": self.id}
#        if position in ["before", "after"]:
#            list_args[position] = target_block.id
#
#        with self._client.as_atomic_transaction():
#
#            # First, remove the node, before we re-insert and re-activate it at the target location
#            self.remove()
#
#            if not self.is_alias:
#                # Set the parent_id of the moving block to the new parent, and mark it as active again
#                self._client.submit_transaction(
#                    build_operation(
#                        id=self.id,
#                        path=[],
#                        args={
#                            "alive": True,
#                            "parent_id": new_parent_id,
#                            "parent_table": new_parent_table,
#                        },
#                        command="update",
#                    )
#                )
#            else:
#                self._alias_parent = new_parent_id
#
#            # Add the moving block's ID to the "content" list of the new parent
#            self._client.submit_transaction(
#                build_operation(
#                    id=new_parent_id,
#                    path=["content"],
#                    args=list_args,
#                    command=list_command,
#                )
#            )
#
#        # update the local block cache to reflect the updates
#        self._client.refresh_records(
#            block=[
#                self.id,
#                self.get("parent_id"),
#                target_block.id,
#                target_block.get("parent_id"),
#            ]
#        )

#    def change_lock(self, locked):
#        command = "update"
#        arguments = dict(
#            block_locked=locked, block_locked_by=self._client.current_user.id
#        )
#
#        with self._client.as_atomic_transaction():
#            self._client.submit_transaction(
#                build_operation(
#                    id=self.id, path=["format"], args=arguments, command=command,
#                )
#            )
#
#        # update the local block cache to reflect the updates
#        self._client.refresh_records(block=[self.id])


class Children:

    child_list_key = "content"

    def __init__(self, parent):
        self._parent = parent
        self._client = parent._client

    def filter(self, type=None):
        kids = list(self)
        if type:
            if isinstance(type, str):
                type = all_block_types().get(type, Block)
            kids = [kid for kid in kids if isinstance(kid, type)]
        return kids

    def _content_list(self) -> list:
        return self._parent.get(self.child_list_key) or []

    def _get_block(self, url_or_id: str):
        # NOTE: this is needed because there seems to be a server-side
        #       race condition with setting and getting data
        #       (sometimes the data previously sent hasn't yet
        #       propagated to all DB nodes, perhaps? it fails to load here)
        for i in range(20):
            block = self._client.get_block(url_or_id)
            if block:
                break
            time.sleep(0.1)
        else:
            return None

        if block.get("parent_id") != self._parent.id:
            block._alias_parent = self._parent.id

        return block

    def __repr__(self):
        if not len(self):
            return "[]"

        children = ""
        for child in self:
            children += f"  {repr(child)},\n"

        return f"[\n{children}]"

    def __len__(self):
        return len(self._content_list() or [])

    def __getitem__(self, key):
        result = self._content_list()[key]
        if not isinstance(result, list):
            return self._get_block(result)

        return [self._get_block(block_id) for block_id in result]

    def __delitem__(self, key):
        self._get_block(self._content_list()[key]).remove()

    def __iter__(self):
        return iter(self._get_block(block_id) for block_id in self._content_list())

    def __reversed__(self):
        return reversed(list(self))

    def __contains__(self, item: Union[str, Block]):
        if isinstance(item, str):
            item_id = extract_id(item)
        elif isinstance(item, Block):
            item_id = item.id
        else:
            return False

        return item_id in self._content_list()

    def add_new(self, block: Block, child_list_key: str = None, **kwargs):
        """
        Create a new block, add it as the last child of this
        parent block, and return the corresponding Block instance.

        Arguments
        ---------
        block : Block
            Class of block to use.

        child_list_key : str, optional
            Defaults to None.
        """

        # determine the block type string from the Block class, if that's what was provided
        is_a_valid_block = isinstance(block, type) and issubclass(block, Block)
        is_a_valid_block = is_a_valid_block and hasattr(block, "_type")
        if not is_a_valid_block:
            raise ValueError(
                "block argument must be a a Block subclass with a _type attribute"
            )

        block_id = self._client.create_record(
            table="block",
            parent=self._parent,
            type=block._type,
            child_list_key=child_list_key,
        )

        block = self._get_block(block_id)

        if kwargs:
            with self._client.as_atomic_transaction():
                for key, val in kwargs.items():
                    if hasattr(block, key):
                        setattr(block, key, val)
                    else:
                        logger.warning(
                            "{} does not have attribute '{}' to be set; skipping.".format(
                                block, key
                            )
                        )

        return block


#    def add_alias(self, block):
#        """
#        Adds an alias to the provided `block`, i.e. adds the block's ID to the parent's content list,
#        but doesn't change the block's parent_id.
#        """
#
#        # add the block to the content list of the parent
#        self._client.submit_transaction(
#            build_operation(
#                id=self._parent.id,
#                path=[self.child_list_key],
#                args={"id": block.id},
#                command="listAfter",
#            )
#        )
#
#        return self._get_block(block.id)


class Templates(Children):

    child_list_key = "template_pages"

    def _content_list(self):
        return self._parent.get(self.child_list_key) or []

    def add_new(self, **kwargs):
        kwargs["block_type"] = "page"
        kwargs["child_list_key"] = self.child_list_key
        kwargs["is_template"] = True

        return super().add_new(**kwargs)
