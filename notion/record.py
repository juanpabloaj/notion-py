from copy import deepcopy
from typing import Callable, Union, Iterable, Any

from notion.settings import BASE_URL
from notion.store import Callback
from notion.utils import extract_id, get_by_path


class Record:
    """
    Basic collection of information about a notion-like block.
    """

    _type = ""
    _table = ""
    _str_fields = "id"
    _child_list_key = None

    def __init__(self, client, block_id: str, *args, **kwargs):
        """
        Create record object and fill its fields.
        """
        self._children = None
        self._callbacks = []
        self._client = client
        self._id = extract_id(block_id)

        if self._client._monitor is not None:
            self._client._monitor.subscribe(self)

    def __repr__(self) -> str:
        """
        Return string representation of the object.


        Returns
        -------
        str
            String with details about the object.
        """
        fields = {}
        klass_chain = self.__class__.__mro__[:-1]

        for klass in reversed(klass_chain):
            for f in self._get_str_fields(klass):
                v = getattr(self, f)
                if v:
                    fields[f] = f"{f}={repr(v)}"

        # skip printing type if its something else than just a Block
        if getattr(klass_chain[0], "_type", "") != "block":
            fields.pop("type", None)

        joined_fields = ", ".join(fields.values())
        return f"<{self.__class__.__name__} ({joined_fields})>"

    def __hash__(self) -> int:
        """
        Unique value computed based on the ID.


        Returns
        -------
        int
            Computed hash value.
        """
        return hash(self.id)

    def __eq__(self, other) -> bool:
        """
        Compare the objects by their ID.


        Arguments
        ---------
        other : Record
            Other record to compare.


        Returns
        -------
        bool
            Whether or not the objects are the same.
        """
        return self.id == other.id

    def __ne__(self, other):
        """
        Compare the objects by their ID.


        Arguments
        ---------
        other : Record
            Other record to compare.


        Returns
        -------
        bool
            Whether or not the objects are different.
        """
        return self.id != other.id

    @staticmethod
    def _get_str_fields(klass) -> list:
        """
        Get list of fields that should be used for printing the Record.

        Returns
        -------
        list
            List of strings.
        """
        str_fields = getattr(klass, "_str_fields", [])

        if isinstance(str_fields, str):
            return [str_fields]

        elif isinstance(str_fields, Iterable):
            return list(str_fields)

        else:
            raise ValueError(
                f"{klass.__name__}._str_fields is not an iterable or a str"
            )

    def _convert_diff_to_changelist(self, difference: list, old_val, new_val) -> list:
        """
        Convert difference between field values into a changelist.


        Arguments
        ---------
        difference : list
            List of changes needed to consider.

        old_val
            Previous value.

        new_val
            New value.


        Returns
        -------
        list
            Changelist converted from different values.
        """
        changed_values = set()
        for operation, path, values in deepcopy(difference):
            path = path.split(".") if isinstance(path, str) else path
            if operation in ["add", "remove"]:
                path.append(values[0][0])
            while isinstance(path[-1], int):
                path.pop()
            changed_values.add(".".join(map(str, path)))

        return [
            (
                "changed_value",
                path,
                (get_by_path(path, old_val), get_by_path(path, new_val)),
            )
            for path in changed_values
        ]

    def _get_record_data(self, force_refresh: bool = False) -> dict:
        """
        Get record data.


        Arguments
        ---------
        force_refresh : bool, optional
            Whether or not to force object refresh.
            Defaults to False.


        Returns
        -------
        dict
            Record data.
        """
        return self._client.get_record_data(
            self._table, self.id, force_refresh=force_refresh
        )

    @property
    def space_info(self):
        data = {"blockId": self.id}
        return self._client.post("getPublicPageData", data=data).json()

    @property
    def url(self) -> str:
        """
        Get the URL.


        Returns
        -------
        str
            URL ro Record.
        """
        return f'{BASE_URL}{self.id.replace("-", "")}'

    @property
    def id(self) -> str:
        """
        Get the Record ID.


        Returns
        -------
        str
            Record ID
        """
        return self._id

    @property
    def role(self) -> str:
        """
        Get the Record role.


        Returns
        -------
        str
            Record role
        """
        return self._client._store.get_role(self._table, self._id)

    def add_callback(
        self, cb: Callable, cb_id: str = "", **extra_kwargs: dict
    ) -> Callback:
        """
        Add callback function to listeners.


        Arguments
        ---------
        cb : Callable
            Function that should be called.

        cb_id : str, optional
            Identification key for the callback.
            Defaults to random UUID string.

        extra_kwargs : dict, optional
            Additional information that should be passed
            to callback when executed.
            Defaults to empty dict.


        Returns
        -------
        Callback
            Callback object.
        """
        cb = self._client._store.add_callback(
            self, cb, callback_id=cb_id, extra_kwargs=extra_kwargs
        )
        self._callbacks.append(cb)
        return cb

    def remove_callbacks(self, cb_or_cb_id_prefix: Union[Callback, str] = None):
        """
        Remove one or more callbacks based on their ID prefix.


        Arguments
        ---------
        cb_or_cb_id_prefix: Callback or str, optional
            Callback to remove or prefix of callback IDs to remove.
        """
        if cb_or_cb_id_prefix is None:
            for callback_obj in list(self._callbacks):
                self._client._store.remove_callbacks(
                    table=self._table,
                    record_id=self.id,
                    cb_or_cb_id_prefix=callback_obj,
                )
            self._callbacks = []

        else:
            self._client._store.remove_callbacks(
                table=self._table,
                record_id=self.id,
                cb_or_cb_id_prefix=cb_or_cb_id_prefix,
            )
            if cb_or_cb_id_prefix in self._callbacks:
                self._callbacks.remove(cb_or_cb_id_prefix)

    def get(
        self,
        path: str = "",
        default: Any = None,
        force_refresh: bool = False,
    ) -> dict:
        """
        Retrieve cached data for this record.


        Arguments
        ---------
        path : str, optional
            Specifies the field to retrieve the value for.
            If no path is supplied, return the entire cached
            data structure for this record.
            Defaults to empty string.

        default : Any, optional
            Default value to return if no value was found
            under provided path.
            Defaults to None.

        force_refresh : bool, optional
            If set to True, force refresh the data cache
            from the server before reading the values.
            Defaults to False.


        Returns
        -------
        dict
            Cached data.
        """
        obj = self._get_record_data(force_refresh=force_refresh)
        return get_by_path(path=path, obj=obj, default=default)

    def set(self, path: str, value: Any):
        """
        Set a specific `value` under the specific `path`
        on the record's data structure on the server.


        Arguments
        ---------
        path : str
            Specifies the field to which set the value.

        value : Any
            Value to set under provided path.
        """
        self._client.build_and_submit_transaction(
            record_id=self.id,
            path=path,
            args=value,
            command="set",
            table=self._table,
        )

    def refresh(self):
        """
        Update the cached data for this record from the server.

        Data for other records may be updated as a side effect.
        """
        self._get_record_data(force_refresh=True)
