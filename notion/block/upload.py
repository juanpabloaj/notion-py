import os
from mimetypes import guess_type

import requests

from notion.settings import S3_URL_PREFIX
from notion.block.embed import EmbedBlock
from notion.maps import field_map, property_map


class UploadBlock(EmbedBlock):

    file_id = field_map(["file_ids", 0])

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
        resp = self._client.post("getUploadFileUrl", data).json()

        with open(path, mode="rb") as f:
            response = requests.put(
                resp["signedPutUrl"], data=f, headers={"Content-type": content_type}
            )
            response.raise_for_status()

        self.display_source = resp["url"]
        self.source = resp["url"]
        self.file_id = resp["url"][len(S3_URL_PREFIX) :].split("/")[0]


class FileBlock(UploadBlock):

    _type = "file"

    size = property_map("size")
    title = property_map("title")


class PdfBlock(UploadBlock):

    _type = "pdf"


class VideoBlock(UploadBlock):

    _type = "video"


class AudioBlock(UploadBlock):

    _type = "audio"


class ImageBlock(UploadBlock):

    _type = "image"
