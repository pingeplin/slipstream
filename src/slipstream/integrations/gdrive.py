import io
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pydantic import BaseModel, ConfigDict, Field


class DownloadResult(BaseModel):
    """Result from downloading a single file.

    Attributes:
        success: Whether the download succeeded
        file_id: The Google Drive file ID
        dest_path: Local path where the file was downloaded
        error: Error message (only present if success=False)
    """

    model_config = ConfigDict(frozen=True)  # Make immutable for safety

    success: bool = Field(..., description="Whether the download succeeded")
    file_id: str = Field(..., description="The Google Drive file ID")
    dest_path: Path = Field(..., description="Local path where file was downloaded")
    error: str | None = Field(
        None, description="Error message (only present if success=False)"
    )


def download_single_file(file_info: dict, dest_dir: Path) -> DownloadResult:
    """Helper function to download a single file and return a result.

    Creates a thread-local service object to avoid SSL/threading issues.

    Args:
        file_info: Dictionary with 'id' and 'name' keys
        dest_dir: Destination directory path

    Returns:
        DownloadResult with success status, file_id, dest_path, and optional error
    """
    file_id = file_info["id"]
    file_name = file_info["name"]
    dest_path = dest_dir / file_name

    try:
        # Create a thread-local service to avoid SSL/threading issues
        thread_service = build("drive", "v3")
        request = thread_service.files().get_media(fileId=file_id)
        with io.FileIO(str(dest_path), "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()

        return DownloadResult(
            success=True,
            file_id=file_id,
            dest_path=dest_path,
            error=None,
        )
    except Exception as e:
        return DownloadResult(
            success=False,
            file_id=file_id,
            dest_path=dest_path,
            error=str(e),
        )


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

    def download_files(
        self, files: list[dict], dest_dir: Path
    ) -> "Generator[DownloadResult, None, None]":
        """Download multiple files in parallel, yielding results as they complete.

        This generator yields download results as soon as each file finishes
        downloading, enabling downstream processing to start immediately
        without waiting for all downloads to complete.

        Args:
            files: List of file dictionaries with 'id' and 'name' keys
            dest_dir: Destination directory path

        Yields:
            DownloadResult dictionaries with:
                - success: bool indicating if download succeeded
                - file_id: the file ID
                - dest_path: path where a file was downloaded
                - error: error message (only if success=False)
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all download tasks
            future_to_file = {
                executor.submit(download_single_file, file_info, dest_dir): file_info
                for file_info in files
            }

            # Yield results as they complete (streaming)
            for future in as_completed(future_to_file):
                yield future.result()
