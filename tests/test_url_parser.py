import pytest

from src.slipstream.utils.url_parser import URLParserError, parse_google_id


@pytest.mark.parametrize(
    ("input_str", "expected_id"),
    [
        # Milestone 1: Raw ID
        ("1AbCdEfGhIjKlMnOpQrStUvWxYz", "1AbCdEfGhIjKlMnOpQrStUvWxYz"),
        # Milestone 2: Google Drive Folders
        (
            "https://drive.google.com/drive/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz",
            "1AbCdEfGhIjKlMnOpQrStUvWxYz",
        ),
        (
            "https://drive.google.com/drive/u/0/folders/1AbCdEfGhIjKlMnOpQrStUvWxYz",
            "1AbCdEfGhIjKlMnOpQrStUvWxYz",
        ),
        (
            "https://drive.google.com/drive/folders/1AbCd?usp=sharing",
            "1AbCd",
        ),
        # Milestone 3: Google Drive Files
        (
            "https://drive.google.com/file/d/1XyZwVuTsRqPoNmLkJiHgFeDcBa/view?usp=drivesdk",
            "1XyZwVuTsRqPoNmLkJiHgFeDcBa",
        ),
        # Milestone 4: Google Sheets
        (
            "https://docs.google.com/spreadsheets/d/1XyZwVuTsRqPoNmLkJiHgFeDcBa/edit#gid=0",
            "1XyZwVuTsRqPoNmLkJiHgFeDcBa",
        ),
    ],
)
def test_parse_google_id(input_str, expected_id):
    assert parse_google_id(input_str) == expected_id


@pytest.mark.parametrize(
    ("input_str", "match"),
    [
        # Milestone 5: Edge Cases and Errors
        ("https://dropbox.com/s/12345", "Unsupported URL domain"),
        ("https://drive.google.com/drive/folders/", "Could not find ID in URL"),
        ("   ", "Input string cannot be empty or whitespace"),
    ],
)
def test_parse_google_id_errors(input_str, match):
    with pytest.raises(URLParserError, match=match):
        parse_google_id(input_str)
