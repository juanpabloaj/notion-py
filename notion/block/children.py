import time
from typing import Union

from notion.block.basic import Block
from notion.block.types import all_block_types
from notion.logger import logger
from notion.operations import build_operation
from notion.utils import extract_id


class Children:

    child_list_key = "content"

    def __init__(self, parent):
        self._parent = parent
        self._client = parent._client

    def filter(self, type=None) -> list:
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

    def add_new(self, block: Block, child_list_key: str = None, **kwargs) -> Block:
        """
        Create a new block, add it as the last child of this
        parent block, and return the corresponding Block instance.


        Arguments
        ---------
        block : Block
            Class of block to use.

        child_list_key : str, optional
            Defaults to None.


        Returns
        -------
        Block
            Instance of added block.
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

    def add_alias(self, block: Block) -> Block:
        """
        Adds an alias to the provided `block`, i.e. adds the block's ID to the parent's content list,
        but doesn't change the block's parent_id.


        Arguments
        ---------
        block : Block
            Instance of block to alias.


        Returns
        -------
        Block
            Aliased block.
        """

        # add the block to the content list of the parent
        self._client.submit_transaction(
            build_operation(
                id=self._parent.id,
                path=[self.child_list_key],
                args={"id": block.id},
                command="listAfter",
            )
        )

        return self._get_block(block.id)


class Templates(Children):
    """
    Templates

    TODO: what? what does that even mean to user?
    """

    child_list_key = "template_pages"

    def _content_list(self):
        return self._parent.get(self.child_list_key) or []

    def add_new(self, **kwargs):
        kwargs["block_type"] = "page"
        kwargs["child_list_key"] = self.child_list_key
        kwargs["is_template"] = True

        return super().add_new(**kwargs)
