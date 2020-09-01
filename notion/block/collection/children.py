import time

from notion.block.children import Children


# TODO: rename to CollectionViews?
class CollectionViewBlockViews(Children):
    """
    Collection View Block Views.
    """

    child_list_key = "view_ids"

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
                "Collection view block does not have an associated collection: {}".format(
                    self._parent
                )
            )

        record_id = self._client.create_record(
            table="collection_view", parent=self._parent, type=view_type
        )
        view = self._client.get_collection_view(
            record_id, collection=self._parent.collection
        )
        view.set("collection_id", self._parent.collection.id)
        view_ids = self._parent.get(CollectionViewBlockViews.child_list_key, [])
        view_ids.append(view.id)
        self._parent.set(CollectionViewBlockViews.child_list_key, view_ids)

        # At this point, the view does not seem to be completely initialized yet.
        # Hack: wait a bit before e.g. setting a query.
        # Note: temporarily disabling this sleep to see if the issue reoccurs.
        # time.sleep(3)
        return view
