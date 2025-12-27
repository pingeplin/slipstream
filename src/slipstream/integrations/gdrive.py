import io

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class GDriveClient:
    def __init__(self):
        self.service = build("drive", "v3")

    def list_files(self, folder_id, mime_types=None):
        query = f"'{folder_id}' in parents"
        if mime_types:
            mime_query = " or ".join([f"mimeType='{m}'" for m in mime_types])
            query += f" and ({mime_query})"

        results = (
            self.service.files()
            .list(q=query, fields="files(id, name, mimeType)")
            .execute()
        )
        return results.get("files", [])

    def download_file(self, file_id, dest_path):
        request = self.service.files().get_media(fileId=file_id)
        with io.FileIO(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
