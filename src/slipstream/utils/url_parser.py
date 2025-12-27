import re
from urllib.parse import urlparse


class URLParserError(ValueError):
    """Raised when a URL cannot be parsed for a Google ID."""


# Regex patterns for different Google URL formats
PATTERNS = [
    # Google Drive Folders: /drive/folders/{ID} or /drive/u/0/folders/{ID}
    re.compile(r"/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)"),
    # Google Drive Files: /file/d/{ID}/view
    re.compile(r"/file/d/([a-zA-Z0-9_-]+)"),
    # Google Sheets: /spreadsheets/d/{ID}/edit
    re.compile(r"/spreadsheets/d/([a-zA-Z0-9_-]+)"),
]


def parse_google_id(input_str: str) -> str:
    """
    Parses a Google Drive or Google Sheets URL to extract the ID.
    If the input is already an ID, it returns it as-is.
    """
    if not input_str or not input_str.strip():
        raise URLParserError("Input string cannot be empty or whitespace")

    if not input_str.startswith("http"):
        return input_str

    parsed = urlparse(input_str)

    if parsed.netloc not in ("drive.google.com", "docs.google.com"):
        raise URLParserError("Unsupported URL domain")

    for pattern in PATTERNS:
        match = pattern.search(parsed.path)
        if match:
            return match.group(1)

    raise URLParserError("Could not find ID in URL")
