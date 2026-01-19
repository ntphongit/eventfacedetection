"""Face detection and search service using DeepFace."""
from pathlib import Path
from dataclasses import dataclass
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


class FaceService:
    """Thin wrapper around DeepFace API."""

    def __init__(self):
        cfg = get_config()
        self.model = cfg["deepface"]["model_name"]
        self.detector = cfg["deepface"]["detector_backend"]
        self.threshold = cfg["deepface"]["threshold"]
        self.db_path = cfg["storage"]["event_photos"]

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

            results = DeepFace.search(
                img=str(temp_path),
                model_name=self.model,
                detector_backend=self.detector,
                distance_metric="cosine",
                database_type="postgres",
                connection_details=self._get_db_connection(),
                search_method="exact",
                k=limit,
                enforce_detection=False
            )

            matches = []
            for df in results:
                if hasattr(df, 'iterrows'):
                    for _, row in df.head(limit).iterrows():
                        dist = row.get("distance", 1.0)
                        matches.append(SearchMatch(
                            image_path=row.get("identity", row.get("img_name", "")),
                            distance=dist,
                            confidence=max(0, 1 - dist)
                        ))

            return sorted(matches, key=lambda x: x.distance)[:limit]

        finally:
            temp_path.unlink(missing_ok=True)

    def register_event_photos(self, photos_dir: str | None = None) -> int:
        """Register all event photos to PostgreSQL using DeepFace.register()."""
        target_dir = photos_dir or self.db_path
        target_path = Path(target_dir)
        image_extensions = {'.jpg', '.jpeg', '.png', '.heic'}

        # Get all image files
        image_files = [
            f for f in target_path.rglob("*")
            if f.is_file() and f.suffix.lower() in image_extensions
        ]

        count = 0
        for img_file in image_files:
            try:
                # Store full absolute path as img_name for retrieval
                full_path = str(img_file.resolve())
                DeepFace.register(
                    img=full_path,
                    img_name=full_path,
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
        """Clear all registered face embeddings from PostgreSQL.

        Returns the number of deleted records.
        """
        import psycopg2

        conn_details = self._get_db_connection()
        # DeepFace uses table name based on model: {model_name}_representations
        table_name = f"{self.model.lower()}_representations"

        conn = psycopg2.connect(
            host=conn_details["host"],
            port=conn_details["port"],
            user=conn_details["user"],
            password=conn_details["password"],
            dbname=conn_details["dbname"]
        )
        try:
            with conn.cursor() as cur:
                # Get count before deletion
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cur.fetchone()[0]

                # Delete all records
                cur.execute(f"DELETE FROM {table_name}")
                conn.commit()
                return count
        except psycopg2.errors.UndefinedTable:
            # Table doesn't exist yet
            return 0
        finally:
            conn.close()
