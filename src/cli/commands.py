"""CLI commands for face detection."""
import click
import subprocess
import platform
from pathlib import Path

from src.services.face_service import FaceService
from src.utils.config_loader import load_config
from src.exceptions import NoFaceDetectedError, MultipleFacesError


def open_path(path: str) -> None:
    """Open file or folder using system default app."""
    if platform.system() == "Darwin":
        subprocess.run(["open", path], check=False)
    elif platform.system() == "Windows":
        subprocess.run(["explorer", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


@click.group()
def cli():
    """Event Face Detection CLI."""
    load_config()


@cli.command()
@click.option("--photos", default=None, help="Event photos directory")
def register(photos: str | None):
    """Register event photos to database."""
    service = FaceService()
    target = photos or service.db_path

    click.echo(f"Registering photos from: {target}")
    count = service.register_event_photos(target)
    click.echo(f"Registered {count} photos.")


@cli.command()
@click.option("--db-path", default=None, help="Event photos directory")
def build(db_path: str | None):
    """Pre-build face representations for event photos."""
    service = FaceService()
    if db_path:
        service.db_path = db_path

    click.echo(f"Building representations for: {service.db_path}")
    count = service.build_representations()
    click.echo(f"Processed {count} photos. Cache ready.")


def _search_single_image(
    service: FaceService, image_path: Path, limit: int,
    open_results: bool, debug: bool
) -> None:
    """Handle single image search (existing behavior)."""
    try:
        content = image_path.read_bytes()

        if debug:
            click.echo("=" * 60)
            click.echo("DEBUG MODE - Face Detection Analysis")
            click.echo("=" * 60)
            matches = service.search_with_debug(content, limit=limit, source_path=str(image_path))
        else:
            matches = service.search(content, limit=limit)

        if not matches:
            click.echo("No matches found.")
            return

        click.echo(f"Found {len(matches)} matches:\n")
        for i, m in enumerate(matches, 1):
            relative_path = m.image_path
            full_path = service.resolve_image_path(relative_path)
            filename = Path(relative_path).name
            click.echo(f"{i}. {filename}")
            click.echo(f"   Relative: {relative_path}")
            click.echo(f"   Full path: {full_path}")
            click.echo(f"   Confidence: {m.confidence:.2%}")
            click.echo()

        if open_results and matches:
            click.echo("Opening matched images...")
            for m in matches:
                full_path = service.resolve_image_path(m.image_path)
                if Path(full_path).exists():
                    open_path(full_path)

    except NoFaceDetectedError as e:
        click.echo(f"Error: {e}", err=True)
    except MultipleFacesError as e:
        click.echo(f"Error: {e}", err=True)


def _search_person_folder(
    service: FaceService, folder_path: Path, limit: int, open_results: bool
) -> None:
    """Handle folder-based person search."""
    person_name = folder_path.name.replace("_", " ")
    click.echo(f"Searching for: {person_name}")
    click.echo(f"Reference folder: {folder_path}")
    click.echo("-" * 50)

    try:
        result = service.search_person_folder(str(folder_path), limit=limit)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        return

    click.echo(f"\nPerson: {result.person_name}")
    click.echo(f"References used: {result.reference_count}")
    click.echo(f"Unique matches: {len(result.matches)}")

    if result.search_errors:
        click.echo(f"\nWarnings ({len(result.search_errors)}):")
        for err in result.search_errors[:5]:
            click.echo(f"  - {err}")

    if not result.matches:
        click.echo("\nNo matches found.")
        return

    # Copy to output folder
    click.echo("\nCopying matches to output folder...")
    output = service.copy_matches_to_output(result)

    click.echo(f"\nCopied {output.copied_count} images to:")
    click.echo(f"  {output.output_path}")

    if output.skipped_files:
        click.echo(f"\nSkipped ({len(output.skipped_files)}):")
        for skip in output.skipped_files[:5]:
            click.echo(f"  - {skip}")

    if open_results and output.copied_count > 0:
        click.echo("\nOpening output folder...")
        open_path(output.output_path)


@cli.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.option("--limit", "-n", default=10, help="Max results")
@click.option("--db-path", default=None, help="Event photos directory (for resolving relative paths)")
@click.option("--open", "-o", "open_results", is_flag=True, help="Open matched images or output folder")
@click.option("--debug", "-d", is_flag=True, help="Show debug info for face detection")
def search(image_path: str, limit: int, db_path: str | None, open_results: bool, debug: bool):
    """Search for matching faces in event photos.

    Accepts single image file OR folder with multiple reference photos.
    When folder provided, extracts person name and copies matches to output.
    """
    service = FaceService()
    if db_path:
        service.set_photos_base_dir(db_path)

    input_path = Path(image_path)

    # Auto-detect: folder = person search, file = single image search
    if input_path.is_dir():
        _search_person_folder(service, input_path, limit, open_results)
    else:
        _search_single_image(service, input_path, limit, open_results, debug)


@cli.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def clear(yes: bool):
    """Clear all registered images from database."""
    service = FaceService()

    if not yes:
        click.confirm("Delete all registered face embeddings?", abort=True)

    count = service.clear_database()
    click.echo(f"Cleared {count} registered images from database.")


@cli.command()
def config():
    """Show current configuration."""
    from src.utils.config_loader import get_config
    import yaml
    click.echo(yaml.dump(get_config(), default_flow_style=False))


if __name__ == "__main__":
    cli()
