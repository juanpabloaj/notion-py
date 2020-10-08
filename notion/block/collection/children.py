import time

from notion.block.children import Children


class CollectionViewBlockViews(Children):
    """
    Collection View Block Views.
    """

    _child_list_key = "view_ids"

    def _get_block(self, view_id):
        view = self._client.get_collection_view(
            view_id, collection=self._parent.collection
        )

        i = 0
        while view is None:
            i += 1
            if i > 20:
                return None
            time.sleep(0.1)
            view = self._client.get_collection_view(
                view_id, collection=self._parent.collection
            )

        return view

    # TODO: why this is not aligned?
    def add_new(self, view_type="table"):
        if not self._parent.collection:
            raise Exception(
                "Collection view block does not have an "
                f"associated collection: {self._parent}"
            )

        record_id = self._client.create_record(
            table="collection_view", parent=self._parent, type=view_type
        )
        view = self._client.get_collection_view(
            record_id, collection=self._parent.collection
        )
        view.set("collection_id", self._parent.collection.id)
        views = self._parent.get(CollectionViewBlockViews._child_list_key, [])
        views.append(view.id)
        self._parent.set(CollectionViewBlockViews._child_list_key, views)

        return view
