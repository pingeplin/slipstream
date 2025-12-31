"""Unit tests for Receipt to Google Sheets row mapping."""

import pytest

from slipstream.integrations.gsheets import receipt_to_sheet_row
from slipstream.models import Receipt, ReceiptItem

pytestmark = pytest.mark.unit


def test_receipt_to_sheet_row_basic():
    """Test converting a basic Receipt to a 5-column sheet row."""
    receipt = Receipt(
        merchant_name="Test Store",
        date="2024-01-15",
        currency="USD",
        total_amount=123.45,
        confidence_score=0.95,
        raw_text="Receipt text here",
    )

    row = receipt_to_sheet_row(receipt)

    assert row == ["Test Store", "2024-01-15", "USD", 123.45, ""]
    assert len(row) == 5


def test_receipt_to_sheet_row_with_default_currency():
    """Test converting a Receipt with default TWD currency."""
    receipt = Receipt(
        merchant_name="台北商店",
        date="2024-12-28",
        total_amount=1500.0,
        confidence_score=0.9,
        raw_text="Receipt text",
    )

    row = receipt_to_sheet_row(receipt)

    assert row == ["台北商店", "2024-12-28", "TWD", 1500.0, ""]


def test_receipt_to_sheet_row_with_items():
    """Test that items are ignored - only summary data is included."""
    receipt = Receipt(
        merchant_name="Store With Items",
        date="2024-01-20",
        currency="EUR",
        total_amount=234.56,
        items=[
            ReceiptItem(description="Item 1", quantity=2, unit_price=10.0, amount=20.0),
            ReceiptItem(
                description="Item 2", quantity=1, unit_price=214.56, amount=214.56
            ),
        ],
        confidence_score=0.95,
        raw_text="Receipt with items",
    )

    row = receipt_to_sheet_row(receipt)

    # Items should be ignored, only summary data
    assert row == ["Store With Items", "2024-01-20", "EUR", 234.56, ""]
    assert len(row) == 5


def test_receipt_to_sheet_row_with_optional_fields():
    """Test that optional fields (tax, payment_method, etc.) are ignored."""
    receipt = Receipt(
        merchant_name="Complete Store",
        date="2024-02-15",
        currency="JPY",
        total_amount=5000.0,
        tax=500.0,
        payment_method="Credit Card",
        invoice_number="INV-12345",
        confidence_score=0.98,
        raw_text="Complete receipt",
    )

    row = receipt_to_sheet_row(receipt)

    # Only the 5 summary columns (4 data + 1 image URL)
    assert row == ["Complete Store", "2024-02-15", "JPY", 5000.0, ""]


def test_receipt_to_sheet_row_with_special_characters():
    """Test handling merchant names with special characters."""
    receipt = Receipt(
        merchant_name="Café & Restaurant™",
        date="2024-03-10",
        currency="USD",
        total_amount=45.99,
        confidence_score=0.9,
        raw_text="Receipt",
    )

    row = receipt_to_sheet_row(receipt)

    assert row == ["Café & Restaurant™", "2024-03-10", "USD", 45.99, ""]


def test_receipt_to_sheet_row_with_decimal_total():
    """Test handling various decimal formats for total amount."""
    receipt = Receipt(
        merchant_name="Decimal Store",
        date="2024-04-05",
        currency="USD",
        total_amount=0.99,
        confidence_score=0.95,
        raw_text="Receipt",
    )

    row = receipt_to_sheet_row(receipt)

    assert row == ["Decimal Store", "2024-04-05", "USD", 0.99, ""]


def test_receipt_to_sheet_row_with_large_total():
    """Test handling large total amounts."""
    receipt = Receipt(
        merchant_name="Expensive Store",
        date="2024-05-20",
        currency="USD",
        total_amount=99999.99,
        confidence_score=0.9,
        raw_text="Receipt",
    )

    row = receipt_to_sheet_row(receipt)

    assert row == ["Expensive Store", "2024-05-20", "USD", 99999.99, ""]


def test_receipt_to_sheet_row_preserves_order():
    """Test that the column order is consistent: Merchant, Date, Currency, Total, Image URL."""
    receipt = Receipt(
        merchant_name="Order Test",
        date="2024-06-15",
        currency="GBP",
        total_amount=75.50,
        confidence_score=0.95,
        raw_text="Receipt",
    )

    row = receipt_to_sheet_row(receipt)

    # Verify order matches expected: [商家, 日期, 幣別, 總計, 圖片連結]
    assert row[0] == "Order Test"  # Merchant
    assert row[1] == "2024-06-15"  # Date
    assert row[2] == "GBP"  # Currency
    assert row[3] == 75.50  # Total
    assert row[4] == ""  # Image URL (empty when no file_id)


def test_receipt_to_sheet_row_with_file_id():
    """Test converting a Receipt with file_id includes image URL as 5th column."""
    receipt = Receipt(
        merchant_name="Test Store",
        date="2024-12-28",
        currency="USD",
        total_amount=150.50,
        confidence_score=0.95,
        raw_text="Test receipt",
        file_id="abc123def456",
    )

    row = receipt_to_sheet_row(receipt)

    assert len(row) == 5
    assert row == [
        "Test Store",
        "2024-12-28",
        "USD",
        150.50,
        "https://drive.google.com/file/d/abc123def456/view",
    ]


def test_receipt_to_sheet_row_without_file_id():
    """Test converting a Receipt without file_id includes empty string as 5th column."""
    receipt = Receipt(
        merchant_name="Test Store",
        date="2024-12-28",
        currency="USD",
        total_amount=150.50,
        confidence_score=0.95,
        raw_text="Test receipt",
    )

    row = receipt_to_sheet_row(receipt)

    assert len(row) == 5
    assert row == ["Test Store", "2024-12-28", "USD", 150.50, ""]


def test_receipt_to_sheet_row_url_format():
    """Test that the URL format is correct for Google Drive."""
    receipt = Receipt(
        merchant_name="Store",
        date="2024-12-28",
        currency="TWD",
        total_amount=299.0,
        confidence_score=0.95,
        raw_text="Receipt",
        file_id="test-file-id-789",
    )

    row = receipt_to_sheet_row(receipt)

    url = row[4]
    assert url.startswith("https://drive.google.com/file/d/")
    assert url.endswith("/view")
    assert "test-file-id-789" in url


def test_receipt_to_sheet_row_column_order():
    """Test that image_url is the 5th column in the correct position."""
    receipt = Receipt(
        merchant_name="Store",
        date="2024-12-28",
        currency="TWD",
        total_amount=100.0,
        confidence_score=0.95,
        raw_text="Receipt",
        file_id="file123",
    )

    row = receipt_to_sheet_row(receipt)

    # Verify order: [商家, 日期, 幣別, 總計, 圖片連結]
    assert row[0] == "Store"  # Merchant
    assert row[1] == "2024-12-28"  # Date
    assert row[2] == "TWD"  # Currency
    assert row[3] == 100.0  # Total
    assert row[4] == "https://drive.google.com/file/d/file123/view"  # Image URL
