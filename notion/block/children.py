import time
from typing import Union, Optional, List

from notion.block.basic import Block
from notion.logger import logger
from notion.utils import extract_id


class Children:

    _child_list_key = "content"

    def __init__(self, parent):
        self._parent = parent
        self._client = parent._client

    def __repr__(self):
        children = "\n" if len(self) else ""
        for child in self:
            children += f"  {repr(child)},\n"

        return f"<{self.__class__.__name__} [{children}]>"

    def __len__(self):
        return len(self._content_list())

    def __getitem__(self, key) -> Union[Optional[Block], List[Optional[Block]]]:
        result = self._content_list()[key]
        if not isinstance(result, list):
            return self._get_block(result)

        return [self._get_block(block_id) for block_id in result]

    def __delitem__(self, key):
        self._get_block(self._content_list()[key]).remove()

    def __iter__(self):
        return iter(self._get_block(bid) for bid in self._content_list())

    def __reversed__(self):
        return reversed(list(self))

    def __contains__(self, other: Union[Block, str]):
        return extract_id(other) in self._content_list()

    def _content_list(self) -> list:
        return self._parent.get(self._child_list_key) or []

    def _get_block(self, url_or_id: str) -> Optional[Block]:
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

    def add_new(
        self, block: Block, child_list_key: str = None, **kwargs
    ) -> Optional[Block]:
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
        # determine the block type string from the Block class, if provided
        valid = isinstance(block, type)
        valid = valid and issubclass(block, Block)
        valid = valid and hasattr(block, "_type")
        if not valid:
            raise ValueError(
                "block argument must be a Block subclass with a _type attribute"
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
                            f"{block} does not have attribute '{key}'; skipping."
                        )

        return block

    def add_alias(self, block: Block) -> Optional[Block]:
        """
        Adds an alias to the provided `block`, i.e. adds
        the block's ID to the parent's content list,
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

        self._client.build_and_submit_transaction(
            record_id=self._parent.id,
            path=self._child_list_key,
            args={"id": block.id},
            command="listAfter",
        )

        return self._get_block(block.id)

    def filter(self, block_type: Union[Block, str]) -> list:
        """
        Get list of children of particular type.


        Arguments
        ---------
        block_type : Block or str
            Block type to filter on.
            Either a Block or block type as str.


        Returns
        -------
        list
            List of blocks.
        """
        if not isinstance(block_type, str):
            block_type = block_type._type

        return [kid for kid in self if kid._type == block_type]


class Templates(Children):
    """
    Templates

    TODO: what? what does that even mean to user?
    """

    _child_list_key = "template_pages"

    def add_new(self, **kwargs) -> Optional[Block]:
        kwargs["block_type"] = "page"
        kwargs["child_list_key"] = self._child_list_key
        kwargs["is_template"] = True

        return super().add_new(**kwargs)
