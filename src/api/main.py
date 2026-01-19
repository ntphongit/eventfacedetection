"""FastAPI application."""
import logging
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.api.schemas import SearchResponse, MatchResult, HealthResponse, RegisterResponse
from src.services.face_service import FaceService
from src.utils.config_loader import load_config, get_config
from src.exceptions import NoFaceDetectedError, MultipleFacesError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_config()
cfg = get_config()

app = FastAPI(
    title="Event Face Detection API",
    version="1.0.0"
)

# Configurable CORS
allowed_origins = cfg.get("api", {}).get("allowed_origins", ["http://localhost:3000"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

service = FaceService()


def validate_path(path: str, allowed_dirs: list[str]) -> bool:
    """Validate path is within allowed directories (prevent path traversal)."""
    resolved = Path(path).resolve()
    for allowed in allowed_dirs:
        allowed_resolved = Path(allowed).resolve()
        try:
            resolved.relative_to(allowed_resolved)
            return True
        except ValueError:
            continue
    return False


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/search", response_model=SearchResponse)
async def search(
    file: UploadFile = File(...),
    limit: int = Query(default=10, ge=1, le=100)
):
    """Search for matching faces."""
    # Validate content type
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    # Read with size limit
    max_size = cfg.get("files", {}).get("max_size_mb", 10) * 1024 * 1024
    content = await file.read(max_size + 1)
    if len(content) > max_size:
        raise HTTPException(413, f"File too large (max {max_size // (1024*1024)}MB)")

    try:
        matches = service.search(content, limit=limit)
        logger.info(f"Search returned {len(matches)} matches")
        return SearchResponse(
            success=True,
            matches=[
                MatchResult(
                    image_path=m.image_path,
                    confidence=m.confidence,
                    distance=m.distance
                )
                for m in matches
            ]
        )

    except NoFaceDetectedError as e:
        logger.warning(f"No face detected: {e}")
        return SearchResponse(success=False, error=str(e))

    except MultipleFacesError as e:
        logger.warning(f"Multiple faces: {e}")
        return SearchResponse(success=False, error=str(e))

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return SearchResponse(success=False, error="Search failed. Please try again.")


@app.post("/register", response_model=RegisterResponse)
async def register(photos_dir: str | None = None):
    """Register event photos to database."""
    # Validate path if provided
    if photos_dir:
        allowed_dirs = cfg.get("storage", {}).get("allowed_directories", [])
        if not validate_path(photos_dir, allowed_dirs):
            logger.warning(f"Path traversal attempt: {photos_dir}")
            raise HTTPException(403, "Access to directory not allowed")

    try:
        count = service.register_event_photos(photos_dir)
        logger.info(f"Registered {count} photos from {photos_dir or 'default'}")
        return RegisterResponse(
            success=True,
            count=count,
            message=f"Registered {count} photos"
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return RegisterResponse(success=False, message="Registration failed. Check logs.")


@app.post("/build")
async def build():
    """Trigger representation building."""
    count = service.build_representations()
    logger.info(f"Built representations for {count} photos")
    return {"message": f"Built representations for {count} photos"}
