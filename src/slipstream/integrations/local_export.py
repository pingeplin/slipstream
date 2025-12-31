"""Local CSV export functionality for receipt data."""

import csv
import fcntl
import os
from pathlib import Path

from slipstream.integrations.gsheets import receipt_to_sheet_row
from slipstream.models import Receipt

# CSV header matching Google Sheets format
CSV_HEADER = ["商家", "日期", "幣別", "總計"]


class LocalExporter:
    """Exporter for writing receipt data to local CSV files.

    This class provides functionality to export receipt data to CSV files
    with the same structure as Google Sheets integration, ensuring consistency
    across both export methods.
    """

    def export(self, receipts: list[Receipt], path: Path) -> None:
        """Export receipts to a local CSV file.

        If the file doesn't exist, it will be created with headers.
        If the file exists, data will be appended to it.

        Args:
            receipts: List of Receipt objects to export
            path: Path to the CSV file to write/append to

        Raises:
            PermissionError: If the file cannot be written due to permissions
            OSError: If there are filesystem-related errors
        """
        # Handle empty receipts list gracefully - don't create file
        if not receipts:
            return

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Always use utf-8 encoding and manually write BOM when creating new file
        # This avoids BOM appearing in the middle when appending
        with open(path, mode="a", encoding="utf-8", newline="") as f:
            # Use file locking to prevent corruption from concurrent writes
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                # Check actual file size AFTER acquiring lock using fstat
                # This is reliable even with concurrent writes
                file_stat = os.fstat(f.fileno())
                is_new_file = file_stat.st_size == 0

                # For new files, write BOM first for Excel compatibility
                if is_new_file:
                    f.write("\ufeff")  # UTF-8 BOM

                writer = csv.writer(f)

                # Write header only if file is new or empty
                if is_new_file:
                    writer.writerow(CSV_HEADER)

                # Write receipt data rows
                for receipt in receipts:
                    row = receipt_to_sheet_row(receipt)
                    writer.writerow(row)
            finally:
                # Release the lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
