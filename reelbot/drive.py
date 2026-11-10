"""Upload a finished video into the chosen Google Drive folder."""
import mimetypes
import os

from googleapiclient.http import MediaFileUpload


def upload_file(drive_service, folder_id, path):
    mime = mimetypes.guess_type(path)[0] or "video/mp4"
    media = MediaFileUpload(path, mimetype=mime, resumable=True, chunksize=8 * 1024 * 1024)
    request = drive_service.files().create(
        body={"name": os.path.basename(path), "parents": [folder_id]},
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    )
    response = None
    while response is None:
        _, response = request.next_chunk(num_retries=3)
    return response["id"]
