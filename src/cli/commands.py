"""CLI commands for face detection."""
import click
from pathlib import Path

from src.services.face_service import FaceService
from src.utils.config_loader import load_config
from src.exceptions import NoFaceDetectedError, MultipleFacesError


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


@cli.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.option("--limit", "-n", default=10, help="Max results")
@click.option("--db-path", default=None, help="Event photos directory")
@click.option("--open", "-o", "open_images", is_flag=True, help="Open matched images")
def search(image_path: str, limit: int, db_path: str | None, open_images: bool):
    """Search for matching faces in event photos."""
    import subprocess
    import platform

    service = FaceService()
    if db_path:
        service.db_path = db_path

    try:
        content = Path(image_path).read_bytes()
        matches = service.search(content, limit=limit)

        if not matches:
            click.echo("No matches found.")
            return

        click.echo(f"Found {len(matches)} matches:\n")
        for i, m in enumerate(matches, 1):
            # Display full path, handle both absolute paths and filenames
            full_path = m.image_path
            filename = Path(full_path).name
            click.echo(f"{i}. {filename}")
            click.echo(f"   Path: {full_path}")
            click.echo(f"   Confidence: {m.confidence:.2%}")
            click.echo()

        # Open images if requested
        if open_images and matches:
            click.echo("Opening matched images...")
            for m in matches:
                img_path = m.image_path
                if Path(img_path).exists():
                    if platform.system() == "Darwin":
                        subprocess.run(["open", img_path], check=False)
                    elif platform.system() == "Windows":
                        subprocess.run(["start", "", img_path], shell=True, check=False)
                    else:
                        subprocess.run(["xdg-open", img_path], check=False)

    except NoFaceDetectedError as e:
        click.echo(f"Error: {e}", err=True)
    except MultipleFacesError as e:
        click.echo(f"Error: {e}", err=True)


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
