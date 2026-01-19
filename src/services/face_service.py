"""Face detection and search service using DeepFace."""
from pathlib import Path
from dataclasses import dataclass
import numpy as np
from deepface import DeepFace

from src.exceptions import NoFaceDetectedError, MultipleFacesError
from src.utils.config_loader import get_config
from src.utils.image_utils import preprocess_image, save_temp


@dataclass
class SearchMatch:
    """Represents a face search match result."""
    image_path: str
    distance: float
    confidence: float
    # Target face bounding box in the matched image
    target_x: int | None = None
    target_y: int | None = None
    target_w: int | None = None
    target_h: int | None = None


@dataclass
class PersonSearchResult:
    """Result from searching with multiple reference photos of one person."""
    person_name: str
    matches: list[SearchMatch]
    reference_count: int
    search_errors: list[str]


@dataclass
class OutputSummary:
    """Summary of copy operation for matched images."""
    copied_count: int
    output_path: str
    skipped_files: list[str]


def find_matching_face_in_image(
    query_embedding: list, image_path: str, model_name: str, detector_backend: str
) -> dict | None:
    """Find the face in an image that best matches the query embedding.

    Args:
        query_embedding: The embedding vector of the query face
        image_path: Path to the image to search in
        model_name: DeepFace model name (e.g., 'Facenet512')
        detector_backend: Face detector backend (e.g., 'retinaface')

    Returns:
        Face dict with 'facial_area' of the best matching face, or None if no match
    """
    # Get embeddings for all detected faces
    representations = DeepFace.represent(
        img_path=image_path, model_name=model_name, detector_backend=detector_backend,
        enforce_detection=False
    )

    if not representations:
        return None

    # Find the face with embedding closest to query
    query_vec = np.array(query_embedding)
    best_face = None
    best_distance = float('inf')

    for rep in representations:
        rep_vec = np.array(rep.get("embedding", []))
        if len(rep_vec) == 0:
            continue
        # Cosine distance
        distance = 1 - np.dot(query_vec, rep_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(rep_vec) + 1e-10)
        if distance < best_distance:
            best_distance = distance
            best_face = {"facial_area": rep.get("facial_area", {})}

    return best_face


class FaceService:
    """Thin wrapper around DeepFace API."""

    def __init__(self):
        cfg = get_config()
        self.model = cfg["deepface"]["model_name"]
        self.detector = cfg["deepface"]["detector_backend"]
        self.threshold = cfg["deepface"]["threshold"]
        self.db_path = cfg["storage"]["event_photos"]
        # Base directory for resolving relative image paths from DB
        self._photos_base_dir: str | None = None

    def set_photos_base_dir(self, base_dir: str) -> None:
        """Set base directory for resolving relative image paths."""
        self._photos_base_dir = str(Path(base_dir).resolve())

    def resolve_image_path(self, relative_path: str) -> str:
        """Convert relative DB path to absolute path for file operations."""
        if Path(relative_path).is_absolute():
            return relative_path  # Already absolute (legacy data)
        base = self._photos_base_dir or self.db_path
        return str(Path(base) / relative_path)

    def validate_single_face(self, image_path: str) -> dict:
        """Ensure exactly one face in image."""
        faces = DeepFace.extract_faces(
            img_path=image_path,
            detector_backend=self.detector,
            enforce_detection=False
        )

        if len(faces) == 0:
            raise NoFaceDetectedError()
        if len(faces) > 1:
            raise MultipleFacesError(len(faces))

        return faces[0]

    def _get_db_connection(self) -> dict:
        """Get PostgreSQL connection details from config."""
        cfg = get_config()
        db = cfg.get("database", {})
        return {
            "host": db.get("host", "localhost"),
            "port": db.get("port", 5432),
            "user": db.get("user", "deepface"),
            "password": db.get("password", "deepface"),
            "dbname": db.get("database", "deepface_db")
        }

    def search(self, query_image: bytes, limit: int = 10) -> list[SearchMatch]:
        """Search for matching faces using DeepFace.search() with PostgreSQL."""
        processed = preprocess_image(query_image)
        temp_path = save_temp(processed)

        try:
            self.validate_single_face(str(temp_path))

            # Use DeepFace.search with similarity_search=True to get all results
            # Then apply our own threshold from config (DeepFace default is too strict)
            results = DeepFace.search(
                img=str(temp_path),
                model_name=self.model,
                detector_backend=self.detector,
                distance_metric="cosine",
                database_type="postgres",
                connection_details=self._get_db_connection(),
                search_method="exact",
                similarity_search=True,  # Return all, apply our threshold later
                k=limit,
                enforce_detection=False
            )

            matches = []
            for df in results:
                if hasattr(df, 'iterrows'):
                    for _, row in df.iterrows():
                        dist = row.get("distance", 1.0)
                        if dist <= self.threshold:
                            matches.append(SearchMatch(
                                image_path=row.get("img_name", ""),
                                distance=dist,
                                confidence=max(0, 1 - dist)
                            ))

            return sorted(matches, key=lambda x: x.distance)[:limit]

        finally:
            temp_path.unlink(missing_ok=True)

    def search_with_debug(self, query_image: bytes, limit: int = 10, source_path: str = "") -> list[SearchMatch]:
        """Search with detailed debug output. Delegates to FaceDebugService."""
        from src.services.face_debug_service import FaceDebugService
        debug_service = FaceDebugService()
        return debug_service.search_with_debug(query_image, limit, source_path)

    def register_event_photos(self, photos_dir: str | None = None) -> int:
        """Register all event photos to PostgreSQL using DeepFace.register().

        Stores relative paths (relative to photos_dir) in the database for portability.
        """
        target_dir = photos_dir or self.db_path
        target_path = Path(target_dir).resolve()
        image_extensions = {'.jpg', '.jpeg', '.png', '.heic'}

        # Set base dir for future path resolution
        self.set_photos_base_dir(str(target_path))

        image_files = [
            f for f in target_path.rglob("*")
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        count = 0
        for img_file in image_files:
            try:
                full_path = str(img_file.resolve())
                # Store relative path in DB for portability
                relative_path = str(img_file.relative_to(target_path))
                DeepFace.register(
                    img=full_path,  # Absolute path for file access
                    img_name=relative_path,  # Relative path stored in DB
                    model_name=self.model,
                    detector_backend=self.detector,
                    database_type="postgres",
                    connection_details=self._get_db_connection(),
                    enforce_detection=False
                )
                count += 1
            except Exception as e:
                print(f"Warning: Failed to register {img_file.name}: {e}")

        return count

    def build_representations(self, photos_dir: str | None = None) -> int:
        """Alias for register_event_photos for CLI compatibility."""
        return self.register_event_photos(photos_dir)

    def clear_database(self) -> int:
        """Clear all registered face embeddings from PostgreSQL."""
        import psycopg2

        conn_details = self._get_db_connection()
        conn = psycopg2.connect(
            host=conn_details["host"],
            port=conn_details["port"],
            user=conn_details["user"],
            password=conn_details["password"],
            dbname=conn_details["dbname"]
        )
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM embeddings")
                count = cur.fetchone()[0]
                cur.execute("DELETE FROM embeddings")
                conn.commit()
                return count
        except psycopg2.errors.UndefinedTable:
            return 0
        finally:
            conn.close()

    def _validate_folder_path(self, folder_path: str) -> Path:
        """Validate folder path against allowed directories.

        Raises:
            ValueError: If folder path is not under allowed directories
        """
        cfg = get_config()
        allowed_dirs = cfg.get("storage", {}).get("allowed_directories", [])

        folder = Path(folder_path).resolve()
        for allowed in allowed_dirs:
            allowed_path = Path(allowed).resolve()
            try:
                folder.relative_to(allowed_path)
                return folder
            except ValueError:
                continue

        raise ValueError(
            f"Folder path not under allowed directories. "
            f"Allowed: {allowed_dirs}"
        )

    def _get_images_from_folder(self, folder_path: str, max_refs: int = 50) -> list[Path]:
        """Get image files from folder (direct children only, limited count).

        Args:
            folder_path: Path to folder
            max_refs: Maximum number of reference images to return
        """
        folder = Path(folder_path)
        cfg = get_config()
        formats = cfg.get("files", {}).get("allowed_formats", ["jpeg", "jpg", "png", "heic"])
        extensions = {f".{fmt.lower()}" for fmt in formats}

        images = [
            f for f in folder.iterdir()
            if f.is_file() and not f.is_symlink() and f.suffix.lower() in extensions
        ]
        return images[:max_refs]

    def search_person_folder(
        self, folder_path: str, limit: int = 50, max_refs: int = 50
    ) -> PersonSearchResult:
        """Search using multiple reference photos from folder.

        Args:
            folder_path: Path to folder with reference photos of ONE person
            limit: Max results per reference search (clamped 1-1000)
            max_refs: Max reference images to process (default 50)

        Returns:
            PersonSearchResult with deduplicated matches (best confidence per image_path)

        Raises:
            ValueError: If folder path not under allowed directories
        """
        # Validate folder path against allowed directories
        validated_folder = self._validate_folder_path(folder_path)

        # Extract person name from folder path (underscore -> space)
        person_name = validated_folder.name.replace("_", " ")

        # Clamp limit to reasonable range
        limit = max(1, min(1000, limit))

        images = self._get_images_from_folder(str(validated_folder), max_refs)
        if not images:
            return PersonSearchResult(person_name, [], 0, ["No images found"])

        # Search with each reference, keep best confidence per image_path
        all_matches: dict[str, SearchMatch] = {}
        errors: list[str] = []

        for img_path in images:
            try:
                content = img_path.read_bytes()
                matches = self.search(content, limit=limit)

                for m in matches:
                    if m.image_path not in all_matches:
                        all_matches[m.image_path] = m
                    elif m.confidence > all_matches[m.image_path].confidence:
                        all_matches[m.image_path] = m

            except NoFaceDetectedError:
                errors.append(f"No face: {img_path.name}")
            except Exception as e:
                errors.append(f"{img_path.name}: {e}")

        # Sort by confidence descending
        sorted_matches = sorted(
            all_matches.values(),
            key=lambda x: x.confidence,
            reverse=True
        )

        return PersonSearchResult(
            person_name=person_name,
            matches=sorted_matches,
            reference_count=len(images),
            search_errors=errors
        )

    def _get_unique_filename(self, dest_dir: Path, filename: str) -> Path:
        """Get unique filename, adding suffix if exists."""
        dest = dest_dir / filename
        if not dest.exists():
            return dest

        stem = Path(filename).stem
        suffix = Path(filename).suffix
        counter = 1
        while dest.exists():
            dest = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        return dest

    def copy_matches_to_output(self, result: PersonSearchResult) -> OutputSummary:
        """Copy matched images to person-specific output folder.

        Args:
            result: PersonSearchResult from search_person_folder

        Returns:
            OutputSummary with copy statistics
        """
        import shutil

        cfg = get_config()
        output_root = cfg.get("person_search", {}).get(
            "output_root", "./results/person_matches"
        )

        person_folder = Path(output_root) / result.person_name
        person_folder.mkdir(parents=True, exist_ok=True)

        copied = 0
        skipped: list[str] = []

        for match in result.matches:
            source_path = Path(self.resolve_image_path(match.image_path))

            if not source_path.exists():
                skipped.append(f"Missing: {match.image_path}")
                continue

            dest_path = self._get_unique_filename(person_folder, source_path.name)

            try:
                shutil.copy2(source_path, dest_path)
                copied += 1
            except Exception as e:
                skipped.append(f"Copy failed {source_path.name}: {e}")

        return OutputSummary(
            copied_count=copied,
            output_path=str(person_folder.resolve()),
            skipped_files=skipped
        )
