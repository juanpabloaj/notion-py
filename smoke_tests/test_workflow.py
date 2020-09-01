import time
import uuid
from datetime import datetime

from notion.block.basic import (
    TextBlock,
    ToDoBlock,
    HeaderBlock,
    SubHeaderBlock,
    PageBlock,
    QuoteBlock,
    BulletedListBlock,
    CalloutBlock,
    ColumnBlock,
    ColumnListBlock,
)
from notion.block.collection.media import CollectionViewBlock
from notion.block.upload import VideoBlock


def test_workflow_1(notion):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parent_page = notion.root_page
    page = parent_page.children.add_new(
        PageBlock,
        title=f"Smoke test at {now}",
    )

    title = "Some formatting: *italic*, **bold**, ***both***!"
    col_list = page.children.add_new(ColumnListBlock)
    col1 = col_list.children.add_new(ColumnBlock)
    col1kid = col1.children.add_new(TextBlock, title=title)

    assert col_list in page.children
    assert col1kid.title.replace("_", "*") == title
    assert col1kid.title_plaintext == "Some formatting: italic, bold, both!"

    col2 = col_list.children.add_new(ColumnBlock)
    col2.children.add_new(ToDoBlock, title="I should be unchecked")
    col2.children.add_new(ToDoBlock, title="I should be checked", checked=True)

    assert col2.children[0].checked is False
    assert col2.children[1].checked is True

    page.children.add_new(HeaderBlock, title="The finest music:")
    video = page.children.add_new(VideoBlock, width=100)
    video.set_source_url("https://www.youtube.com/watch?v=oHg5SJYRHA0")

    assert video in page.children.filter(VideoBlock)
    assert col_list not in page.children.filter(VideoBlock)

    page.children.add_new(SubHeaderBlock, title="A link back to where I came from:")

    alias = page.children.add_alias(parent_page)
    assert alias.is_alias
    assert not page.is_alias

    page.children.add_new(
        QuoteBlock,
        title="Clicking [here]({}) should take you to the same place...".format(
            page.parent.get_browseable_url()
        ),
    )

    # ensure __repr__ methods are not breaking
    repr(page)
    repr(page.children)
    for child in page.children:
        repr(child)

    page.children.add_new(
        SubHeaderBlock, title="The order of the following should be alphabetical:"
    )

    b = page.children.add_new(BulletedListBlock, title="B")
    d = page.children.add_new(BulletedListBlock, title="D")
    c2 = page.children.add_new(BulletedListBlock, title="C2")
    c1 = page.children.add_new(BulletedListBlock, title="C1")
    c = page.children.add_new(BulletedListBlock, title="C")
    a = page.children.add_new(BulletedListBlock, title="A")

    d.move_to(c, "after")
    a.move_to(b, "before")
    c2.move_to(c)
    c1.move_to(c, "first-child")

    page.children.add_new(CalloutBlock, title="I am a callout", icon="🤞")

    cvb = page.children.add_new(CollectionViewBlock)
    cvb.collection = notion.client.get_collection(
        notion.client.create_record(
            "collection", parent=cvb, schema=get_collection_schema()
        )
    )
    cvb.title = "My data!"
    view = cvb.views.add_new(view_type="table")

    special_code = uuid.uuid4().hex[:8]

    # add a row
    row1 = cvb.collection.add_row()
    assert row1.person == []
    row1.name = "Just some data"
    row1.title = "Can reference 'title' field too! " + special_code
    assert row1.name == row1.title
    row1.check_yo_self = True
    row1.estimated_value = None
    row1.estimated_value = 42
    row1.files = [
        "https://www.birdlife.org/sites/default/files/styles/1600/public/slide.jpg"
    ]
    row1.tags = None
    row1.tags = []
    row1.tags = ["A", "C"]
    row1.where_to = "https://learningequality.org"
    row1.category = "A"
    row1.category = ""
    row1.category = None
    row1.category = "B"

    # add another row
    row2 = cvb.collection.add_row(
        person=notion.client.current_user, title="Metallic penguins"
    )
    assert row2.person == [notion.client.current_user]
    assert row2.name == "Metallic penguins"
    row2.check_yo_self = False
    row2.estimated_value = 22
    row2.files = [
        "https://www.picclickimg.com/d/l400/pict/223603662103_/Vintage-Small-Monet-and-Jones-JNY-Enamel-Metallic.jpg"
    ]
    row2.tags = ["A", "B"]
    row2.where_to = "https://learningequality.org"
    row2.category = "C"

    # Run a filtered/sorted query using the view's default parameters
    result = view.default_query().execute()
    assert row1 == result[0]
    assert row2 == result[1]
    assert len(result) == 2

    # query the collection directly
    assert row1 in cvb.collection.get_rows(search=special_code)
    assert row2 not in cvb.collection.get_rows(search=special_code)
    assert row1 not in cvb.collection.get_rows(search="penguins")
    assert row2 in cvb.collection.get_rows(search="penguins")

    # search the entire space
    assert row1 in notion.client.search_blocks(search=special_code)
    assert row1 not in notion.client.search_blocks(search="penguins")
    assert row2 not in notion.client.search_blocks(search=special_code)
    assert row2 in notion.client.search_blocks(search="penguins")

    # Run an "aggregation" query
    aggregations = [
        {"property": "estimated_value", "aggregator": "sum", "id": "total_value"}
    ]
    result = view.build_query(aggregations=aggregations).execute()
    assert result.get_aggregate("total_value") == 64

    # Run a "filtered" query
    filter_params = {
        "filters": [
            {
                "filter": {
                    "value": {
                        "type": "exact",
                        "value": {
                            "table": "notion_user",
                            "id": notion.client.current_user.id,
                        },
                    },
                    "operator": "person_does_not_contain",
                },
                "property": "person",
            }
        ],
        "operator": "and",
    }
    result = view.build_query(filter=filter_params).execute()
    assert row1 in result
    assert row2 not in result

    # Run a "sorted" query
    sort_params = [{"direction": "ascending", "property": "estimated_value"}]
    result = view.build_query(sort=sort_params).execute()
    assert row1 == result[1]
    assert row2 == result[0]

    id = page.id
    parent_page = page.parent

    assert page.get("alive") is True
    assert page in parent_page.children
    page.remove()
    assert page.get("alive") is False
    assert page not in parent_page.children

    assert (
        page.space_info
    ), f"Page {id} was fully deleted prematurely, as we can't get space info about it anymore"

    page.remove(permanently=True)
    time.sleep(1)

    assert (
        not page.space_info
    ), f"Page {id} was not really fully deleted, as we can still get space info about it"


def get_collection_schema():
    return {
        "%9:q": {"name": "Check Yo'self", "type": "checkbox"},
        "=d{|": {
            "name": "Tags",
            "type": "multi_select",
            "options": [
                {
                    "color": "orange",
                    "id": "79560dab-c776-43d1-9420-27f4011fcaec",
                    "value": "A",
                },
                {
                    "color": "default",
                    "id": "002c7016-ac57-413a-90a6-64afadfb0c44",
                    "value": "B",
                },
                {
                    "color": "blue",
                    "id": "77f431ab-aeb2-48c2-9e40-3a630fb86a5b",
                    "value": "C",
                },
            ],
        },
        "=d{q": {
            "name": "Category",
            "type": "select",
            "options": [
                {
                    "color": "orange",
                    "id": "59560dab-c776-43d1-9420-27f4011fcaec",
                    "value": "A",
                },
                {
                    "color": "default",
                    "id": "502c7016-ac57-413a-90a6-64afadfb0c44",
                    "value": "B",
                },
                {
                    "color": "blue",
                    "id": "57f431ab-aeb2-48c2-9e40-3a630fb86a5b",
                    "value": "C",
                },
            ],
        },
        "LL[(": {"name": "Person", "type": "person"},
        "4Jv$": {"name": "Estimated value", "type": "number"},
        "OBcJ": {"name": "Where to?", "type": "url"},
        "dV$q": {"name": "Files", "type": "file"},
        "title": {"name": "Name", "type": "title"},
    }
