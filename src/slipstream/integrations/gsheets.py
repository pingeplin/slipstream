"""Google Sheets integration for writing receipt data.

Note: The Google API Client library uses dynamic method creation at runtime.
Methods like .spreadsheets() are added to Resource objects when build() is called,
so type checkers can't detect them. We use # type: ignore[attr-defined] to
suppress these warnings where appropriate.
"""

from typing import Any

from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from slipstream.integrations.gdrive import generate_file_url
from slipstream.models import Receipt


def _is_retryable_error(exception: BaseException) -> bool:
    """Determine if an exception should trigger a retry.

    Retries on:
    - HTTP 429 (rate limit exceeded)
    - HTTP 503 (service unavailable)
    - Network errors (ConnectionError, TimeoutError, etc.)

    Does NOT retry on:
    - HTTP 400 (bad request - invalid input)
    - HTTP 403 (forbidden - authentication/permission issue)
    - HTTP 404 (not found - invalid spreadsheet ID)
    - Other client errors (4xx)

    Args:
        exception: The exception to check

    Returns:
        True if the exception is retryable, False otherwise
    """
    # Retry on network errors
    if isinstance(exception, ConnectionError | TimeoutError | OSError):
        return True

    # Retry on specific HTTP errors
    if isinstance(exception, HttpError):
        status = exception.resp.status
        # Retry on rate limit (429) and service unavailable (503)
        return status in (429, 503)

    return False


def receipt_to_sheet_row(receipt: Receipt) -> list[Any]:
    """Convert a Receipt model to a Google Sheets row.

    The row contains 5 columns in this order:
    1. 商家 (Merchant) - merchant_name
    2. 日期 (Date) - date (YYYY-MM-DD format)
    3. 幣別 (Currency) - currency
    4. 總計 (Total) - total_amount
    5. 圖片連結 (Image Link) - Google Drive file URL

    Args:
        receipt: The Receipt object to convert

    Returns:
        A list with 5 values: [merchant_name, date, currency, total_amount, image_url]
    """
    return [
        receipt.merchant_name,
        receipt.date,
        receipt.currency,
        receipt.total_amount,
        generate_file_url(receipt.file_id),
    ]


class GSheetsClient:
    """Client for interacting with Google Sheets API.

    Attributes:
        spreadsheet_id: Optional Google Sheets spreadsheet ID
    """

    def __init__(self, spreadsheet_id: str | None = None):
        """Initialize the Google Sheets client.

        Args:
            spreadsheet_id: Optional Google Sheets spreadsheet ID
        """
        self._service: Resource | None = None  # Private cache for lazy initialization
        self.spreadsheet_id = spreadsheet_id

    @property
    def service(self) -> Resource:
        """Lazily initialize and return the Google Sheets service.

        The service is created on first access and cached for subsequent calls.
        This avoids gRPC initialization overhead during instantiation.

        Returns:
            The Google Sheets API service (Resource object)
        """
        if self._service is None:
            self._service = build("sheets", "v4")
        return self._service

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def append_row(
        self, values: list[Any], range_name: str = "Sheet1!A1"
    ) -> dict[str, Any]:
        """Append a single row to the spreadsheet.

        Args:
            values: List of values to append as a row
            range_name: The A1 notation of the range to append to (default: "Sheet1!A1")

        Returns:
            The API response containing update information

        Raises:
            ValueError: If spreadsheet_id is not set
            HttpError: For non-retryable errors or after max retries
        """
        if not self.spreadsheet_id:
            raise ValueError("spreadsheet_id must be set before calling append_row")

        # Note: spreadsheets() is dynamically added by googleapiclient at runtime
        result = (
            self.service.spreadsheets()  # type: ignore[attr-defined]
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": [values]},
            )
            .execute()
        )
        return result

    @retry(
        retry=retry_if_exception(_is_retryable_error),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def append_rows(
        self, rows: list[list[Any]], range_name: str = "Sheet1!A1"
    ) -> dict[str, Any]:
        """Append multiple rows to the spreadsheet in a batch operation.

        Args:
            rows: List of rows, where each row is a list of values
            range_name: The A1 notation of the range to append to (default: "Sheet1!A1")

        Returns:
            The API response containing update information

        Raises:
            ValueError: If spreadsheet_id is not set
            HttpError: For non-retryable errors or after max retries
        """
        if not self.spreadsheet_id:
            raise ValueError("spreadsheet_id must be set before calling append_rows")

        # Note: spreadsheets() is dynamically added by googleapiclient at runtime
        result = (
            self.service.spreadsheets()  # type: ignore[attr-defined]
            .values()
            .append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": rows},
            )
            .execute()
        )
        return result
