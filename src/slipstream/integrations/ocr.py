"""OCR Engine using Google Cloud Vision API for receipt text extraction."""

from pathlib import Path

from google.cloud import vision


class OCREngine:
    """
    OCR Engine for extracting text from receipt images using Google Vision API.

    This class provides a simple interface to Google Cloud Vision's text detection
    capabilities, specifically optimized for receipt processing.
    """

    def __init__(self, client: vision.ImageAnnotatorClient | None = None) -> None:
        """
        Initialize the OCR Engine.

        Args:
            client: Optional pre-configured ImageAnnotatorClient.
                   If None, a default client will be created.
        """
        self.client = client or vision.ImageAnnotatorClient()

    def extract_text(self, image_path: str) -> str:
        """
        Extract text from an image file using Google Vision API.

        Args:
            image_path: Path to the image file to process.

        Returns:
            Extracted text as a string. Returns empty string if no text is found.

        Raises:
            FileNotFoundError: If the image file does not exist.
            google.api_core.exceptions.GoogleAPIError: If the API call fails.
        """
        # Validate file exists and is a file (not a directory)
        path = Path(image_path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        # Read image file
        with path.open("rb") as image_file:
            content = image_file.read()

        # Create Vision API image object
        image = vision.Image(content=content)

        # Perform text detection
        response = self.client.text_detection(image=image)

        # Extract text from response
        if response.text_annotations:
            # The first annotation contains the entire detected text
            return response.text_annotations[0].description

        return ""
