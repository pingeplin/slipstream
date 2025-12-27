import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


class GDriveClient:
    def __init__(self, max_workers: int = 4):
        self.service = build("drive", "v3")
        self.max_workers = max_workers

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

    def download_files(self, files: list[dict], dest_dir: Path) -> list[dict]:
        """Download multiple files in parallel using ThreadPoolExecutor.

        Args:
            files: List of file dictionaries with 'id' and 'name' keys
            dest_dir: Destination directory path

        Returns:
            List of result dictionaries containing:
                - success: bool indicating if download succeeded
                - file_id: the file ID
                - dest_path: path where file was downloaded
                - error: error message (only if success=False)
        """
        results = []

        def _download_single_file(file_info: dict) -> dict:
            """Helper function to download a single file and return result.

            Creates a thread-local service object to avoid SSL/threading issues.
            """
            file_id = file_info["id"]
            file_name = file_info["name"]
            dest_path = Path(dest_dir) / file_name

            try:
                # Create a thread-local service to avoid SSL/threading issues
                thread_service = build("drive", "v3")
                request = thread_service.files().get_media(fileId=file_id)
                with io.FileIO(str(dest_path), "wb") as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()

                return {
                    "success": True,
                    "file_id": file_id,
                    "dest_path": dest_path,
                }
            except Exception as e:
                return {
                    "success": False,
                    "file_id": file_id,
                    "dest_path": dest_path,
                    "error": str(e),
                }

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_file = {
                executor.submit(_download_single_file, file_info): file_info
                for file_info in files
            }

            # Collect results as they complete
            for future in as_completed(future_to_file):
                result = future.result()
                results.append(result)

        return results
