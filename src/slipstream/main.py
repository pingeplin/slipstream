import tempfile
from pathlib import Path

import typer

from slipstream.integrations.gdrive import GDriveClient
from slipstream.utils.url_parser import URLParserError, parse_google_id

app = typer.Typer()


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

    with tempfile.TemporaryDirectory() as tmp_dir:
        for file in files:
            try:
                dest_path = Path(tmp_dir) / file["name"]
                client.download_file(file["id"], str(dest_path))
                typer.echo(f"Downloaded {file['name']}")
            except Exception as e:
                typer.echo(f"Failed to download {file['name']}: {e}", err=True)
                # Continue with the next file as per PRD "Continue-on-error mode"


def main():
    app()


if __name__ == "__main__":
    main()
