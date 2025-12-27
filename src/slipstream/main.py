import asyncio
import os
import tempfile
from pathlib import Path

import typer
from dotenv import load_dotenv

from slipstream.integrations.anthropic_extractor import (
    AnthropicExtractor,
    ExtractionError,
    ExtractionIncompleteError,
    ExtractionRefusedError,
)
from slipstream.integrations.gdrive import GDriveClient
from slipstream.integrations.ocr import OCREngine
from slipstream.utils.url_parser import URLParserError, parse_google_id

load_dotenv()

app = typer.Typer(no_args_is_help=True)


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context):
    """Slipstream CLI tool."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


@app.command()
def process(
    folder: str = typer.Option(
        ..., "--folder", "-f", help="Google Drive folder ID or URL"
    ),
):
    """Process files from a Google Drive folder."""
    try:
        folder_id = parse_google_id(folder)
    except URLParserError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1) from e

    typer.echo(f"Processing folder: {folder_id}")

    try:
        client = GDriveClient()
        files = client.list_files(
            folder_id, mime_types=["image/jpeg", "image/png", "application/pdf"]
        )
    except Exception as e:
        typer.echo(f"Error communicating with Google Drive: {e}", err=True)
        raise typer.Exit(code=1) from e

    if not files:
        typer.echo("No supported files found in folder.")
        return

    # Initialize OCR engine
    try:
        ocr_engine = OCREngine()
    except Exception as e:
        typer.echo(f"Failed to initialize OCR engine: {e}", err=True)
        raise typer.Exit(code=1) from e

    # Initialize Anthropic extractor
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        typer.echo(
            "Warning: ANTHROPIC_API_KEY not found. Skipping LLM extraction.",
            err=True,
        )
        extractor = None
    else:
        try:
            extractor = AnthropicExtractor(api_key=anthropic_api_key)
        except Exception as e:
            typer.echo(f"Failed to initialize Anthropic extractor: {e}", err=True)
            raise typer.Exit(code=1) from e

    with tempfile.TemporaryDirectory() as tmp_dir:
        for file in files:
            try:
                dest_path = Path(tmp_dir) / file["name"]
                client.download_file(file["id"], str(dest_path))
                typer.echo(f"Downloaded {file['name']}")

                # Process with OCR
                try:
                    text = ocr_engine.extract_text(str(dest_path))
                    typer.echo(
                        f"Extracted text from {file['name']}: {len(text)} characters"
                    )

                    # Process with LLM if extractor is available
                    if extractor:
                        try:
                            result = asyncio.run(extractor.extract_receipt_data(text))
                            typer.echo(
                                f"Structured data extracted for {file['name']}: "
                                f"{result.receipt.merchant_name}, "
                                f"{result.receipt.date}, "
                                f"${result.receipt.total_amount:.2f} "
                                f"{result.receipt.currency}"
                            )
                        except ExtractionRefusedError as e:
                            typer.echo(
                                f"Failed to extract structured data from "
                                f"{file['name']}: {e}",
                                err=True,
                            )
                            # Continue with next file (continue-on-error mode)
                        except ExtractionIncompleteError as e:
                            typer.echo(
                                f"Failed to extract structured data from "
                                f"{file['name']}: {e}",
                                err=True,
                            )
                            # Continue with next file (continue-on-error mode)
                        except ExtractionError as e:
                            typer.echo(
                                f"Failed to extract structured data from "
                                f"{file['name']}: {e}",
                                err=True,
                            )
                            # Continue with next file (continue-on-error mode)
                        except Exception as llm_error:
                            typer.echo(
                                f"Failed to extract structured data from "
                                f"{file['name']}: {llm_error}",
                                err=True,
                            )
                            # Continue with next file (continue-on-error mode)

                except Exception as ocr_error:
                    typer.echo(
                        f"Failed to extract text from {file['name']}: {ocr_error}",
                        err=True,
                    )
                    # Continue with next file (continue-on-error mode)
            except Exception as e:
                typer.echo(f"Failed to download {file['name']}: {e}", err=True)
                # Continue with the next file as per PRD "Continue-on-error mode"


def main():
    app()


if __name__ == "__main__":
    main()
