"""Unit tests for local CSV export functionality."""

import csv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from slipstream.integrations.local_export import LocalExporter
from slipstream.models import Receipt


@pytest.fixture
def sample_receipt() -> Receipt:
    """Create a sample receipt for testing."""
    return Receipt(
        merchant_name="Test Store",
        date="2024-12-28",
        total_amount=150.50,
        currency="TWD",
        confidence_score=0.95,
        raw_text="Test raw text",
    )


@pytest.fixture
def sample_receipt_with_unicode() -> Receipt:
    """Create a sample receipt with Chinese characters."""
    return Receipt(
        merchant_name="全聯福利中心",
        date="2024-12-28",
        total_amount=299.00,
        currency="TWD",
        confidence_score=0.98,
        raw_text="Test raw text with unicode",
    )


@pytest.fixture
def sample_receipts() -> list[Receipt]:
    """Create a list of sample receipts for testing."""
    return [
        Receipt(
            merchant_name="Store A",
            date="2024-12-28",
            total_amount=100.00,
            currency="TWD",
            confidence_score=0.95,
            raw_text="Receipt A",
        ),
        Receipt(
            merchant_name="Store B",
            date="2024-12-29",
            total_amount=200.00,
            currency="USD",
            confidence_score=0.92,
            raw_text="Receipt B",
        ),
    ]


def test_export_receipts_creates_file(tmp_path: Path, sample_receipt: Receipt) -> None:
    """Verify that calling export creates the file if it doesn't exist."""
    export_path = tmp_path / "receipts.csv"
    exporter = LocalExporter()

    # File should not exist before export
    assert not export_path.exists()

    # Export should create the file
    exporter.export([sample_receipt], export_path)

    # File should now exist
    assert export_path.exists()
    assert export_path.is_file()


def test_export_receipts_content_consistency(
    tmp_path: Path, sample_receipt: Receipt
) -> None:
    """Verify that the CSV content matches expected fields and order."""
    export_path = tmp_path / "receipts.csv"
    exporter = LocalExporter()

    exporter.export([sample_receipt], export_path)

    # Read the CSV file
    with open(export_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Should have header + 1 data row
    assert len(rows) == 2

    # Check header (商家, 日期, 幣別, 總計)
    assert rows[0] == ["商家", "日期", "幣別", "總計"]

    # Check data row matches receipt fields
    assert rows[1] == [
        sample_receipt.merchant_name,
        sample_receipt.date,
        sample_receipt.currency,
        str(sample_receipt.total_amount),
    ]


def test_export_receipts_appends_to_existing(
    tmp_path: Path, sample_receipts: list[Receipt]
) -> None:
    """Verify that subsequent calls append data instead of overwriting."""
    export_path = tmp_path / "receipts.csv"
    exporter = LocalExporter()

    # First export
    exporter.export([sample_receipts[0]], export_path)

    # Second export should append
    exporter.export([sample_receipts[1]], export_path)

    # Read the CSV file
    with open(export_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Should have header + 2 data rows
    assert len(rows) == 3
    assert rows[0] == ["商家", "日期", "幣別", "總計"]

    # First receipt
    assert rows[1][0] == "Store A"

    # Second receipt (appended)
    assert rows[2][0] == "Store B"


def test_export_receipts_unicode_handling(
    tmp_path: Path, sample_receipt_with_unicode: Receipt
) -> None:
    """Verify that Chinese characters are correctly preserved."""
    export_path = tmp_path / "receipts.csv"
    exporter = LocalExporter()

    exporter.export([sample_receipt_with_unicode], export_path)

    # Read the CSV file with utf-8-sig encoding
    with open(export_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Check that Chinese characters in header are preserved
    assert rows[0] == ["商家", "日期", "幣別", "總計"]

    # Check that Chinese characters in data are preserved
    assert rows[1][0] == "全聯福利中心"


def test_export_receipts_empty_data(tmp_path: Path) -> None:
    """Verify that an empty list of receipts handles gracefully."""
    export_path = tmp_path / "receipts.csv"
    exporter = LocalExporter()

    # Export empty list
    exporter.export([], export_path)

    # File should not be created for empty data
    assert not export_path.exists()


def test_export_receipts_error_handling(
    tmp_path: Path, sample_receipt: Receipt
) -> None:
    """Verify handling of PermissionError or non-existent parent directories."""
    # Test 1: Non-existent parent directory should be created
    export_path = tmp_path / "subdir" / "receipts.csv"
    exporter = LocalExporter()

    assert not export_path.parent.exists()

    exporter.export([sample_receipt], export_path)

    assert export_path.exists()
    assert export_path.parent.exists()

    # Test 2: PermissionError should be raised for invalid paths
    # On Unix systems, /dev/null cannot be used as a directory
    invalid_path = Path("/dev/null/receipts.csv")

    with pytest.raises((PermissionError, OSError, FileNotFoundError)):
        exporter.export([sample_receipt], invalid_path)


def test_export_receipts_concurrent_writes(
    tmp_path: Path, sample_receipts: list[Receipt]
) -> None:
    """Verify that concurrent writes do not corrupt the file."""
    export_path = tmp_path / "receipts.csv"
    exporter = LocalExporter()

    # Create multiple receipts for concurrent writing
    receipts_batch = [
        Receipt(
            merchant_name=f"Store {i}",
            date="2024-12-28",
            total_amount=float(i * 100),
            currency="TWD",
            confidence_score=0.95,
            raw_text=f"Receipt {i}",
        )
        for i in range(10)
    ]

    # Write concurrently using ThreadPoolExecutor
    def write_receipt(receipt: Receipt) -> None:
        exporter.export([receipt], export_path)

    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(write_receipt, receipts_batch)

    # Read the CSV file
    with open(export_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)

    # Should have header + 10 data rows
    # Note: The first write creates the header, subsequent writes append data only
    assert len(rows) == 11  # 1 header + 10 data rows
    assert rows[0] == ["商家", "日期", "幣別", "總計"]

    # Verify all receipts were written (order may vary due to concurrency)
    merchant_names = {row[0] for row in rows[1:]}
    expected_names = {f"Store {i}" for i in range(10)}
    assert merchant_names == expected_names
