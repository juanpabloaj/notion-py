import re

from commonmark import Parser
from commonmark.dump import prepare

delimiters = {
    "!",
    '"',
    "#",
    "$",
    "%",
    "&",
    "'",
    "(",
    ")",
    "*",
    "+",
    ",",
    "-",
    ".",
    "/",
    ":",
    ";",
    "<",
    "=",
    ">",
    "?",
    "@",
    "[",
    "\\",
    "]",
    "^",
    "_",
    "`",
    "{",
    "|",
    "}",
    "~",
    "☃",
    " ",
    "\t",
    "\n",
    "\x0b",
    "\x0c",
    "\r",
    "\x1c",
    "\x1d",
    "\x1e",
    "\x1f",
    "\x85",
    "\xa0",
    "\u1680",
    "\u2000",
    "\u2001",
    "\u2002",
    "\u2003",
    "\u2004",
    "\u2005",
    "\u2006",
    "\u2007",
    "\u2008",
    "\u2009",
    "\u200a",
    "\u2028",
    "\u2029",
    "\u202f",
    "\u205f",
    "\u3000",
}

_NOTION_TO_MARKDOWN_MAPPER = {"i": "☃", "b": "☃☃", "s": "~~", "c": "`"}

FORMAT_PRECEDENCE = ["s", "b", "i", "a", "c"]


def _extract_text_and_format_from_ast(item: dict):
    literal = item.get("literal", "")
    item_type = item["type"]

    if item_type == "html_inline":
        if literal == "<s>":
            return "", ("s",)

    if item_type == "strong":
        return literal, ("b",)

    if item_type == "emph":
        return literal, ("i",)

    if item_type == "link":
        return literal, ("a", item.get("destination", ""))

    if item_type == "code":
        return literal, ("c",)

    return literal, ()


def _get_format(notion_segment, as_set=False):
    if len(notion_segment) == 1:
        if as_set:
            return set()
        else:
            return []
    else:
        if as_set:
            return set([tuple(f) for f in notion_segment[1]])
        else:
            return notion_segment[1]


def _cleanup_dashes(thing):
    regex_pattern = re.compile("⸻|%E2%B8%BB")
    if type(thing) is list:
        for counter, value in enumerate(thing):
            thing[counter] = _cleanup_dashes(value)
    elif type(thing) is str:
        return regex_pattern.sub("-", thing)

    return thing


def markdown_to_notion(markdown: str) -> list:
    """
    Convert Markdown formatted string to Notion.


    Arguments
    ---------
    markdown : str
        Text to convert.


    Returns
    -------
    list of Block
        Blocks converted from input.
    """

    # commonmark doesn't support strikethrough,
    # so we need to handle it ourselves
    while markdown.count("~~") >= 2:
        markdown = markdown.replace("~~", "<s>", 1)
        markdown = markdown.replace("~~", "</s>", 1)

    # we don't want to touch dashes, so temporarily replace them here
    markdown = markdown.replace("-", "⸻")

    parser = Parser()
    ast = prepare(parser.parse(markdown))

    format = set()

    notion = []

    for section in ast:

        _, ended_format = _extract_text_and_format_from_ast(section)
        if ended_format and ended_format in format:
            format.remove(ended_format)

        if section["type"] == "paragraph":
            notion.append(["\n\n"])

        for item in section.get("children", []):

            literal, new_format = _extract_text_and_format_from_ast(item)

            if new_format:
                format.add(new_format)

            if item["type"] == "html_inline" and literal == "</s>":
                format.remove(("s",))
                literal = ""

            if item["type"] == "softbreak":
                literal = "\n"

            if literal:
                notion.append(
                    [literal, [list(f) for f in sorted(format)]]
                    if format
                    else [literal]
                )

            # in the ast format, code blocks are meant
            # to be immediately self-closing
            if ("c",) in format:
                format.remove(("c",))

    # remove any trailing newlines from automatic closing paragraph markers
    if notion:
        notion[-1][0] = notion[-1][0].rstrip("\n")

    # consolidate any adjacent text blocks with identical styles
    consolidated = []
    for item in notion:
        if consolidated and _get_format(consolidated[-1], as_set=True) == _get_format(
            item, as_set=True
        ):
            consolidated[-1][0] += item[0]
        elif item[0]:
            consolidated.append(item)

    return _cleanup_dashes(consolidated)


# TODO: Rewrite this function, it has to be shorter!
def notion_to_markdown(notion: list) -> str:
    """
    Convert list of notion blocks to markdown text.


    Arguments
    ---------
    notion : list
        List of Notion Blocks
        TODO: is it true?


    Raises
    ------
    Exception
        When it's unable to extract text.


    Returns
    -------
    str
        Converted Markdown text.
    """
    pattern = re.compile(r"^(?P<leading>\s*)(?P<stripped>(\s|.)*?)(?P<trailing>\s*)$")
    markdown_chunks = []

    for item in notion or []:

        markdown = ""

        text = item[0]
        format = item[1] if len(item) == 2 else []

        match = pattern.match(text)

        if not match:
            raise Exception("Unable to extract text from: %r" % text)

        leading_whitespace = match.groupdict()["leading"]
        stripped = match.groupdict()["stripped"]
        trailing_whitespace = match.groupdict()["trailing"]

        markdown += leading_whitespace

        sorted_format = sorted(
            format,
            key=lambda x: FORMAT_PRECEDENCE.index(x[0])
            if x[0] in FORMAT_PRECEDENCE
            else -1,
        )

        for f in sorted_format:
            if f[0] in _NOTION_TO_MARKDOWN_MAPPER:
                if stripped:
                    markdown += _NOTION_TO_MARKDOWN_MAPPER[f[0]]
            if f[0] == "a":
                markdown += "["

        markdown += stripped

        for f in reversed(sorted_format):
            if f[0] in _NOTION_TO_MARKDOWN_MAPPER:
                if stripped:
                    markdown += _NOTION_TO_MARKDOWN_MAPPER[f[0]]
            if f[0] == "a":
                markdown += "]({})".format(f[1])

        markdown += trailing_whitespace

        # to make it parseable, add a space after if it combines code/links and emphasis formatting
        format_types = [f[0] for f in format]
        if (
            ("c" in format_types or "a" in format_types)
            and ("b" in format_types or "i" in format_types)
            and not trailing_whitespace
        ):
            markdown += " "

        markdown_chunks.append(markdown)

    # use underscores as needed to separate adjacent chunks to avoid ambiguous runs of asterisks
    full_markdown = ""
    last_used_underscores = False
    for i in range(len(markdown_chunks)):
        prev = markdown_chunks[i - 1] if i > 0 else ""
        curr = markdown_chunks[i]
        next = markdown_chunks[i + 1] if i < len(markdown_chunks) - 1 else ""
        prev_ended_in_delimiter = not prev or prev[-1] in delimiters
        next_starts_with_delimiter = not next or next[0] in delimiters
        if (
            prev_ended_in_delimiter
            and next_starts_with_delimiter
            and not last_used_underscores
            and curr.startswith("☃")
            and curr.endswith("☃")
        ):
            if curr[1] == "☃":
                count = 2
            else:
                count = 1
            curr = "_" * count + curr[count:-count] + "_" * count
            last_used_underscores = True
        else:
            last_used_underscores = False

        final_markdown = curr.replace("☃", "*")

        # to make it parseable, convert emphasis/strong combinations to use a mix of _ and *
        if "***" in final_markdown:
            final_markdown = final_markdown.replace("***", "**_", 1)
            final_markdown = final_markdown.replace("***", "_**", 1)

        full_markdown += final_markdown

    return full_markdown


def notion_to_plaintext(notion: list, client=None) -> str:
    """
    Convert list of notion blocks to plain text.


    Arguments
    ---------
    notion : list
        Text in a Notion specific API format
        i.e. [["some text"]]

    client : NotionClient, optional
        Used for getting blocks, if passed.
        Defaults to None.


    Returns
    -------
    str
        Converted text.
    """
    plaintext = ""

    for item in notion or []:

        text = item[0]
        formats = item[1] if len(item) == 2 else []

        if text == "‣":

            for f in formats:
                if f[0] == "p":  # page link
                    if client is None:
                        plaintext += "page:" + f[1]
                    else:
                        plaintext += client.get_block(f[1]).title_plaintext
                elif f[0] == "u":  # user link
                    if client is None:
                        plaintext += "user:" + f[1]
                    else:
                        plaintext += client.get_user(f[1]).full_name

            continue

        plaintext += text

    return plaintext


def plaintext_to_notion(plaintext: str) -> list:
    """
    Convert plain text to list of notion blocks.


    Arguments
    ---------
    plaintext : str
        Text to be converted.


    Returns
    -------
    list
        List with the converted plaintext.
    """
    return [[plaintext]]
