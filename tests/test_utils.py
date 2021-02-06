from notion.utils import *


def test_split_on_dot():
    assert list(split_on_dot("schema.?m.J.name")) == [
        "schema",
        "schema.",
        "schema.?m",
        "schema.?m.",
        "schema.?m.J",
        "schema.?m.J.",
        "schema.?m.J.name",
    ]

    assert list(split_on_dot("schema.=f)..name")) == [
        "schema",
        "schema.",
        "schema.=f)",
        "schema.=f).",
        "schema.=f)..name",
    ]


def test_get_by_path():
    obj = {
        "schema": {
            ":vHS": {"name": "Column 13", "type": "text"},
            ":{:U": {"name": "Column 20", "type": "text"},
            ";wKV": {"name": "Column 1", "type": "text"},
            "<Q>D": {"name": "Column 11", "type": "text"},
            "?m.J": {"name": "asd", "type": "text"},
            ".yZV": {"name": "Column 14", "type": "text"},
            "AC..": {"name": "Column 19", "type": "text"},
            "=f).": {"name": "Column 20", "type": "text"},
        },
        "something": [
            {"idx1": "neat"},
            {"idx2": "cool"},
            {"idx3": "bruh"},
        ],
    }

    # basic checks
    assert get_by_path("schema.:vHS.name", obj, False) == "Column 13"
    assert get_by_path("schema.:{:U.name", obj, False) == "Column 20"
    assert get_by_path("schema.;wKV.type", obj, False) == "text"
    assert get_by_path("schema.<Q>D", obj, False).__class__.__name__ == "dict"
    assert get_by_path("schema.?m.J.name", obj, False) == "asd"

    # weird dot patterns
    assert get_by_path("schema..yZV.name", obj, False) == "Column 14"
    assert get_by_path("schema.AC...name", obj, False) == "Column 19"
    assert get_by_path("schema.=f)..name", obj, False) == "Column 20"

    # invalid keys
    assert get_by_path("schema..yZV.nam", obj, False) is False
    assert get_by_path("schema.AD...name", obj, False) is False

    # array indexing
    assert get_by_path("something.0.idx1", obj, False) == "neat"
    assert get_by_path("something.1.idx2", obj, False) == "cool"
    assert get_by_path("something.3.idx3", obj, False) is False
    assert get_by_path("something.3", obj, False) is False
