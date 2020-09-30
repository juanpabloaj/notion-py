import logging

from notion.settings import NOTION_LOG_FILE, NOTION_LOG_LEVEL

logger = logging.getLogger("notion")


if NOTION_LOG_LEVEL == "DISABLED":
    handler = logging.NullHandler()
else:
    handler = logging.FileHandler(NOTION_LOG_FILE)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.setLevel(NOTION_LOG_LEVEL)
    handler.setLevel(NOTION_LOG_LEVEL)

logger.addHandler(handler)
