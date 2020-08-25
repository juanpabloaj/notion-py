import os
from pathlib import Path

BASE_URL = "https://www.notion.so/"
API_BASE_URL = BASE_URL + "api/v3/"

SIGNED_URL_PREFIX = "https://www.notion.so/signed/"
MESSAGE_STORE_URL = "https://msgstore.www.notion.so/primus/"

S3_URL_PREFIX = "https://s3-us-west-2.amazonaws.com/secure.notion-static.com/"
S3_URL_PREFIX_ENCODED = "https://s3.us-west-2.amazonaws.com/secure.notion-static.com/"

# for rendering
EMBED_API_URL = "https://api.embed.ly/1/oembed?key=421626497c5d4fc2ae6b075189d602a2"
CHART_API_URL = "https://chart.googleapis.com/chart?cht=tx&chl="
TWITTER_API_URL = "https://publish.twitter.com/oembed?url="

NOTION_DATA_DIR = Path(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~"))
NOTION_DATA_DIR = os.environ.get("NOTION_DATA_DIR", str(NOTION_DATA_DIR / ".notion-py"))
os.makedirs(NOTION_DATA_DIR, exist_ok=True)

NOTION_LOG_FILE = str(Path(NOTION_DATA_DIR) / "notion.log")
NOTION_CACHE_DIR = str(Path(NOTION_DATA_DIR) / "cache")
os.makedirs(NOTION_CACHE_DIR, exist_ok=True)

NOTION_LOG_LEVEL = os.environ.get("NOTION_LOG_LEVEL", "WARNING").upper()
