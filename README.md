<!-- markdownlint-disable no-inline-html first-line-h1 -->

<div align="center">
  <h1>notion-py</h1>
  <h4>(Fork of) Unofficial Python 3 client for Notion.so API v3.</h4>

  [Documentation][documentation-url]
  | [Package on PyPI][package-url]
  <br>
  <br>
  ![check formatting][check-formatting-url]
  ![run unit tests][run-unit-tests-url]  
  ![upload-python-package][upload-python-package-url]
  ![run-smoke-tests][run-smoke-tests-url]
  ![documentation-status][documentation-status-url]  
  ![code-style][code-style-url]
  ![license][license-url]
  ![code-size][code-size-url]
  ![downloads-rate][downloads-rate-url]
</div>
<br>

 


---

> **_NOTE:_**  This is a fork of the 
[original repository](https://github.com/jamalex/notion-py)
created by [Jamie Alexandre](https://github.com/jamalex).
That repository seems to be abandoned.  
I've sent an email to Jamie if I can be a maintainer
but unfortunately I have not received any response,
hence my work on this fork and second package on PyPI.  
You can try out this package - it's called 
[notion-py](https://pypi.org/project/notion-py/)
on PyPI.
The original package created by Jamie is  still online
under the name 
[notion](https://pypi.org/project/notion/) on PyPI,
so please watch out for any confusion.
imports are still working as before, the `-py` in 
name is there only to differentiate between these two.

---
 
These libraries as of now are _not_ fully compatible.

List of major differences:
- imports were changed, especially for blocks and collections.  
  General rule is:
  - `notion.block.py       ->  notion.block.*.py`
  - `notion.collection.py  ->  notion.block.collection.*.py`
- some block names were changed to align them with notion.so  
  One of such examples is `TodoBlock -> ToDoBlock` (because it's type is `to_do`)
- some function definitions also changed  
  I did that to simplify the API and make it more uniform.

<br>
<br>



## Features
- **Automatic conversion between Notion blocks and Python objects**  
  we covered pretty much every block type there is!

- **Callback system for responding to changes in Notion**  
  useful for triggering actions, updating another block, etc.

- **Object-oriented interface**  
  seamless mapping of API response parameters to Python classes/attributes.
  
- **Local cache of data in a unified data store**  
  note: this is disabled by default; add `enable_caching=True` when initializing `NotionClient` to change it.
  
- **Real-time reactive two-way data binding**  
  fancy way of saying that changing Python object will update the Notion UI, and vice-versa.

---

![data binding example][data-binding-url]  
<sup>*(Example of the two-way data binding in action)*</sup>
<br>


[Read more about Notion and the original notion-py package on Jamie's blog][introduction-url].


## Usage

### Quickstart


> **_NOTE:_** The latest version of **notion-py** requires Python 3.6 or greater.


`pip install notion-py`

```Python
from notion.client import NotionClient

# Obtain the `token_v2` value by inspecting your browser 
# cookies on a logged-in (non-guest) session on Notion.so
client = NotionClient(token_v2="123123...")

# Replace this URL with the URL of the page you want to edit
page = client.get_block("https://www.notion.so/myorg/Test-c0d20a71c0944985ae96e661ccc99821")

print("The old title is:", page.title)

# You can use Markdown! We convert on-the-fly 
# to Notion's internal formatted text data structure.
page.title = "The title has now changed, and has *live-updated* in the browser!"
```

## Getting the token_v2

1. Open [notion.so](https://notion.so) in your browser and log in.
2. Open up developer console ([quick tutorial the most common browsers][dev-tools-url]).
3. Find a list of cookies (Firefox: `Storage` -> `Cookies`, Chrome: `Application` -> `Cookies`).
4. Find the one named `token_v2` and copy its value (lengthy, 160ish characters hex string).
5. Save it somewhere safe and use it with notion-py!

> **_NOTE:_** Keep the token in secure place and out of your repository!  
> This token when leaked can let anyone do anything on your notion account!


## Updating records

We keep a local cache of all data that passes through.  
When you reference an attribute on a `Record` (basically
any `Block`) we first look to that cache to retrieve the value.
If it doesn't find it, it retrieves it from the server.
You can also manually refresh the data for a `Record`
by calling the `refresh()` method on it.

By default (unless we instantiate `NotionClient` 
with `monitor=False`), we also subscribe to long-polling 
updates for any instantiated `Record`, so the local cache 
data for these `Records` should be automatically 
live-updated shortly after any data changes on the server.  
The long-polling happens in a background daemon thread.


## Concepts and notes
  
- **The tables we currently support are `block`, `space`,
  `collection`, `collection_view`, and `notion_user`.**

- **We map tables in the Notion database into Python classes**  
  by subclassing `Record`, with each instance of a class
  representing a particular record. Some fields from the
  records (like `title` in the example above) have been
  mapped to model properties, allowing for easy,
  instantaneous read/write of the record.
  Other fields can be read with the `get` method,
  and written with the `set` method, but then you'll 
  need to make sure to match the internal structures exactly.
  
- **Data for all tables are stored in a central RecordStore**  
  with the `Record` instances not storing state internally,
  but always referring to the data in the 
  central `RecordStore`.
  Many API operations return updating versions of a large 
  number of associated records, which we use to update 
  the store, so the data in `Record` instances may sometimes 
  update without being explicitly requested.
  You can also call the `refresh()` method on a `Record` 
  to trigger an update, or pass `force_update=True` to 
  methods like `get()`.
  
- **The API doesn't have strong validation of most data**  
  so be careful to maintain the structures Notion is expecting.
  You can view the full internal structure of a record by 
  calling `myrecord.get()` with no arguments.
  
- **When you call `client.get_block()`, you can pass in 
  block ID, or the URL of a block**  
  Note that pages themselves are just `blocks`, as are all 
  the chunks of content on the page. You can get the URL 
  for a block within a page by clicking "Copy Link" in the 
  context menu for the block, and pass that URL 
  into `get_block()` as well.



## Working on a Pull Request

You'll need `git` and `python3` with `venv` module.  


Best way to start is to clone the repo and prepare the `.env` file.
This step is optional but nice to have to create healthy python venv.

```bash
git https://github.com/arturtamborski/notion-py

cd notion-py

cp .env.example .env
vim .env
```

You should modify the variables as following:
```bash
# see above for info on how to get it
NOTION_TOKEN_V2="insert your token_v2 here"

# used in smoke tests
NOTION_PAGE_URL="insert URL from some notion page here"

# set it to any level from python logging library
NOTION_LOG_LEVEL="DEBUG" 

# the location for cache, defaults to current directory
NOTION_DATA_DIR=".notion-py"
```

And then load that file (which will also create local venv):
```bash
source .env
```

On top of that there's a handy toolbox provided to you via `Makefile`.
Everything related to the development of the project relies heavily on
the interface it provides.

You can display all commands by running
```bash
make help
```

Which should print a nice list of commands avaiable to you.
These are compatible with the Github Actions (CI system),
in fact the actions are using Makefile directly for formatting
and other steps so everything that Github might show you
under your Pull Request can be reproduced locally via Makefile.


Also, there's one very handy shortcut that I'm using all the
time when testing the library with smoke tests.

This command will run a single test unit that you point at
by passing an argument to `make try-smoke-test` like so:

```bash
make try-smoke-test smoke_tests/test_workflow.py::test_workflow_1
```

That's super handy when you run some smoke tests and see the failed output:
```
============================= short test summary info =============================
ERROR smoke_tests/block/test_basic.py::test_block - KeyboardInterrupt
!!!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!!!!!!!!!!!!!!!!!! _pytest.outcomes.Exit: Quitting debugger !!!!!!!!!!!!!!!!!!!!!
================================ 1 error in 32.90s ================================
make: *** [Makefile:84: try-smoke-test] Error 2
```

Notice that `ERROR smoke_tests/...test_basic.py::test_block` - just copy it over
as a command argument and run it again - you'll run this and only this one test!

```bash
make try-smoke-test smoke_tests/block/test_basic.py::test_block
```




## Examples

<details>
<summary><em>Click here to show or hide</em></summary>  


### Example: Traversing the block tree

```Python
for child in page.children:
    print(child.title)

print(f"Parent of {page.id} is {page.parent.id}")
```


### Example: Adding a new node

```Python
from notion.block.basic import ToDoBlock

todo = page.children.add_new(ToDoBlock, title="Something to get done")
todo.checked = True
```


### Example: Deleting nodes

```Python
# soft-delete
page.remove()

# hard-delete
page.remove(permanently=True)
```


### Example: Create an embedded content type (iframe, video, etc)

```Python
from notion.block.upload import VideoBlock

video = page.children.add_new(VideoBlock, width=200)

# sets "property.source" to the URL
# and "format.display_source" to the embedly-converted URL
video.set_source_url("https://www.youtube.com/watch?v=oHg5SJYRHA0")
```


### Example: Create a new embedded collection view block

```Python
from notion.block.collection.basic import CollectionViewBlock

collection = client.get_collection("<some collection ID>") # get an existing collection
cvb = page.children.add_new(CollectionViewBlock, collection=collection)
view = cvb.views.add_new(view_type="table")

# Before the view can be browsed in Notion, 
# the filters and format options on the view should be set as desired.
# 
# for example:
#   view.set("query", ...)
#   view.set("format.board_groups", ...)
#   view.set("format.board_properties", ...)
```


### Example: Moving blocks around

```Python
# move my block to after the video
my_block.move_to(video, "after")

# move my block to the end of otherblock's children
my_block.move_to(otherblock, "last-child")

# Note: you can also use "before" and "first-child" :)
```


### Example: Subscribing to updates

> **_NOTE:_** Notion -> Python automatic updating is 
> currently broken and hence disabled by default.  
> call `my_block.refresh()` to update, in the meantime,
> while monitoring is being fixed.

We can "watch" a `Record` so that we get a callback whenever 
it changes. Combined with the live-updating of records based 
on long-polling, this allows for a "reactive" design, where 
actions in our local application can be triggered in response 
to interactions with the Notion interface.

```Python
# define a callback (all arguments are optional, just include the ones you care about)
def my_callback(record, difference):
    print("The record's title is now:", record.title)
    print("Here's what was changed:\n", difference)

# move my block to after the video
my_block.add_callback(my_callback)
```


### Example: Working with databases, aka "collections" (tables, boards, etc)

Here's how things fit together:
- Main container block: `CollectionViewBlock` (inline) / `CollectionViewPageBlock` (full-page)
    - `Collection` (holds the schema, and is parent to the database rows themselves)
        - `CollectionBlock`
        - `CollectionBlock`
        - ... (more database records)
    - `CollectionView` (holds filters/sort/etc about each specific view)

For convenience, we automatically map the database
"columns" (aka properties), based on the schema defined
in the `Collection`, into getter/setter attributes 
on the `CollectionBlock` instances.

The attribute name is a "slugified" version of the name of 
the column. So if you have a column named "Estimated value", 
you can read and write it via `myrowblock.estimated_value`.

Some basic validation may be conducted, and it will be 
converted into the appropriate internal format.

For columns of type "Person", we expect a `NotionUser` instance, 
or a list of them, and for a "Relation" we expect a singular/list 
of instances of a subclass of `Block`.

```Python
# Access a database using the URL of the database page or the inline block
cv = client.get_collection_view("https://www.notion.so/myorg/b9076...8b832?v=8de...8e1")

# List all the records with "Bob" in them
for row in cv.collection.get_rows(search="Bob"):
    print("We estimate the value of '{}' at {}".format(row.name, row.estimated_value))

# Add a new record
row = cv.collection.add_row()
row.name = "Just some data"
row.is_confirmed = True
row.estimated_value = 399
row.files = ["https://www.birdlife.org/sites/default/files/styles/1600/public/slide.jpg"]
row.person = client.current_user
row.tags = ["A", "C"]
row.where_to = "https://learningequality.org"

# Run a filtered/sorted query using a view's default parameters
result = cv.default_query().execute()
for row in result:
    print(row)

# Run an "aggregation" query
aggregations = [{
    "property": "estimated_value",
    "aggregator": "sum",
    "id": "total_value",
}]
result = cv.build_query(aggregate=aggregations).execute()
print("Total estimated value:", result.get_aggregate("total_value"))

# Run a "filtered" query (inspect network tab in browser for examples, on queryCollection calls)
filters = {
    "filters": [{
        "filter": {
            "value": {
                "type": "exact",
                "value": {"table": "notion_user", "id": client.current_user.id}
            },
            "operator": "person_contains"
        },
        "property": "assigned_to"
    }],
    "operator": "and"
}
result = cv.build_query(filter=filters).execute()
print("Things assigned to me:", result)

# Run a "sorted" query
sorters = [{
    "direction": "descending",
    "property": "estimated_value",
}]
result = cv.build_query(sort=sorters).execute()
print("Sorted results, showing most valuable first:", result)
```

> **_NOTE:_**: You can combine `filter`, `aggregate`, and `sort`.
> See more examples of queries by setting up complex views in Notion,
> and then inspecting `cv.get("query")`.


### Example: Lock/Unlock A Page

```python
from notion.client import NotionClient

client = NotionClient(token_v2="123123...")

# Replace this URL with the URL of the page you want to edit
page = client.get_block("https://www.notion.so/myorg/Test-c0d20a71c0944985ae96e661ccc99821")

# change_lock is a method accessible to every Block/Page in notion.
# Pass True to lock a page and False to unlock it. 
page.change_lock(True)
page.change_lock(False)
```


</details>
<br>


---

### Quick plug: Learning Equality is hiring!

We're a [small nonprofit](https://learningequality.org/)
with [global impact](https://learningequality.org/ka-lite/map/),
building [exciting tech](https://learningequality.org/kolibri/)!
We're currently [hiring](https://grnh.se/6epyi21) -- come join us!


[documentation-url]: https://notion-py.readthedocs.io
[package-url]: https://pypi.org/project/notion-py/
[check-formatting-url]: https://github.com/arturtamborski/notion-py/workflows/Check%20Code%20Formatting/badge.svg
[run-unit-tests-url]: https://github.com/arturtamborski/notion-py/workflows/Run%20Unit%20Tests/badge.svg
[upload-python-package-url]: https://github.com/arturtamborski/notion-py/workflows/Upload%20Python%20Package/badge.svg
[run-smoke-tests-url]: https://github.com/arturtamborski/notion-py/workflows/Run%20Smoke%20Tests/badge.svg
[code-style-url]: https://img.shields.io/badge/code%20style-black-000000
[documentation-status-url]: https://readthedocs.org/projects/notion-py/badge/?version=latest
[license-url]: https://img.shields.io/github/license/arturtamborski/notion-py
[code-size-url]: https://img.shields.io/github/languages/code-size/arturtamborski/notion-py
[downloads-rate-url]: https://img.shields.io/pypi/dm/notion-py.svg

[introduction-url]: https://medium.com/@jamiealexandre/introducing-notion-py-an-unofficial-python-api-wrapper-for-notion-so-603700f92369
[data-binding-url]: https://raw.githubusercontent.com/jamalex/notion-py/master/ezgif-3-a935fdcb7415.gif
[dev-tools-url]: https://support.airtable.com/hc/en-us/articles/232313848-How-to-open-the-developer-console
