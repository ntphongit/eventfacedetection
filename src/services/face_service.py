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
