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
    workers: int = typer.Option(
        4, "--workers", "-w", help="Number of parallel download workers"
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
        client = GDriveClient(max_workers=workers)
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
        # Download all files in parallel
        download_results = client.download_files(files, Path(tmp_dir))

        # Report download results
        for result in download_results:
            if result["success"]:
                typer.echo(f"Downloaded {result['dest_path'].name}")
            else:
                file_name = result["dest_path"].name
                typer.echo(
                    f"Failed to download {file_name}: {result['error']}", err=True
                )

        # Process each successfully downloaded file with OCR and LLM
        for result in download_results:
            if not result["success"]:
                continue

            dest_path = result["dest_path"]
            file_name = dest_path.name
            try:
                # Process with OCR
                text = ocr_engine.extract_text(str(dest_path))
                typer.echo(f"Extracted text from {file_name}: {len(text)} characters")

                # Process with LLM if extractor is available
                if extractor:
                    try:
                        extraction_result = asyncio.run(
                            extractor.extract_receipt_data(text)
                        )
                        typer.echo(
                            f"Structured data extracted for {file_name}: "
                            f"{extraction_result.receipt.merchant_name}, "
                            f"{extraction_result.receipt.date}, "
                            f"${extraction_result.receipt.total_amount:.2f} "
                            f"{extraction_result.receipt.currency}"
                        )
                    except ExtractionRefusedError as e:
                        typer.echo(
                            f"Failed to extract structured data from {file_name}: {e}",
                            err=True,
                        )
                        # Continue with next file (continue-on-error mode)
                    except ExtractionIncompleteError as e:
                        typer.echo(
                            f"Failed to extract structured data from {file_name}: {e}",
                            err=True,
                        )
                        # Continue with next file (continue-on-error mode)
                    except ExtractionError as e:
                        typer.echo(
                            f"Failed to extract structured data from {file_name}: {e}",
                            err=True,
                        )
                        # Continue with next file (continue-on-error mode)
                    except Exception as llm_error:
                        typer.echo(
                            f"Failed to extract structured data from "
                            f"{file_name}: {llm_error}",
                            err=True,
                        )
                        # Continue with next file (continue-on-error mode)

            except Exception as ocr_error:
                typer.echo(
                    f"Failed to extract text from {file_name}: {ocr_error}",
                    err=True,
                )
                # Continue with next file (continue-on-error mode)


def main():
    app()


if __name__ == "__main__":
    main()
