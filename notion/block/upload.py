import os
from mimetypes import guess_type
from urllib.parse import urlencode, urlparse

from notion.block.embed import EmbedBlock
from notion.maps import field_map, property_map
from notion.utils import human_size


class UploadBlock(EmbedBlock):
    """
    Upload Block.
    """

    file_id = field_map("file_ids.0")

    def upload_file(self, path: str):
        """
        Upload a file and embed it in Notion.


        Arguments
        ---------
        path : str
            Valid path to a file.


        Raises
        ------
        HTTPError
            On API error.
        """

        content_type = guess_type(path)[0] or "text/plain"
        file_name = os.path.split(path)[-1]

        data = {"bucket": "secure", "name": file_name, "contentType": content_type}
        resp = self._client.post("getUploadFileUrl", data)
        resp.raise_for_status()
        resp_data = resp.json()
        url = resp_data["url"]
        signed_url = resp_data["signedPutUrl"]

        with open(path, mode="rb") as f:
            headers = {"Content-Type": content_type}
            resp = self._client.put(signed_url, data=f, headers=headers)
            resp.raise_for_status()

        query = urlencode(
            {
                "cache": "v2",
                "name": file_name,
                "id": self._id,
                "table": self._table,
                "userId": self._client.current_user.id,
            }
        )
        query_url = f"{url}?{query}"

        self.source = query_url
        self.display_source = query_url
        self.file_id = urlparse(url).path.split("/")[2]


class FileBlock(UploadBlock):
    """
    File Block.
    """

    _type = "file"

    size = property_map("size")
    title = property_map("title")

    def upload_file(self, path: str):
        super().upload_file(path)
        self.size = human_size(path)


class PdfBlock(UploadBlock):
    """
    PDF Block.
    """

    _type = "pdf"


class VideoBlock(UploadBlock):
    """
    Video Block.
    """

    _type = "video"


class AudioBlock(UploadBlock):
    """
    Audio Block.
    """

    _type = "audio"


class ImageBlock(UploadBlock):
    """
    Image Block.
    """

    _type = "image"
