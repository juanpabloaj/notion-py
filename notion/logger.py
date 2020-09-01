import logging

from notion.settings import NOTION_LOG_FILE, NOTION_LOG_LEVEL

logger = logging.getLogger("notion")


# TODO: test this, I have no idea if this actually works
if NOTION_LOG_LEVEL == "DISABLED":
    handler = logging.NullHandler()
else:
    handler = logging.FileHandler(NOTION_LOG_FILE)
    formatter = logging.Formatter("\n%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.setLevel(NOTION_LOG_LEVEL)
    handler.setLevel(NOTION_LOG_LEVEL)

logger.addHandler(handler)
