"""Debug utilities for face detection analysis."""
from deepface import DeepFace

from src.exceptions import NoFaceDetectedError, MultipleFacesError
from src.utils.config_loader import get_config
from src.utils.image_utils import preprocess_image, save_temp, save_face_debug_image, save_match_debug_image
from src.services.face_service import SearchMatch, find_matching_face_in_image


class FaceDebugService:
    """Debug service for face detection analysis."""

    def __init__(self):
        cfg = get_config()
        self.model = cfg["deepface"]["model_name"]
        self.detector = cfg["deepface"]["detector_backend"]
        self.threshold = cfg["deepface"]["threshold"]
        self._db_cfg = cfg.get("database", {})
        self._photos_base_dir = cfg["storage"]["event_photos"]

    def resolve_image_path(self, relative_path: str) -> str:
        """Convert relative DB path to absolute path for file operations."""
        from pathlib import Path
        if Path(relative_path).is_absolute():
            return relative_path  # Already absolute (legacy data)
        return str(Path(self._photos_base_dir) / relative_path)

    def _get_db_connection(self) -> dict:
        return {
            "host": self._db_cfg.get("host", "localhost"),
            "port": self._db_cfg.get("port", 5432),
            "user": self._db_cfg.get("user", "deepface"),
            "password": self._db_cfg.get("password", "deepface"),
            "dbname": self._db_cfg.get("database", "deepface_db")
        }

    def search_with_debug(self, query_image: bytes, limit: int = 10, source_path: str = "") -> list[SearchMatch]:
        """Search with detailed debug output showing face detection steps."""
        from PIL import Image
        import io
        import os

        print(f"\n[1] INPUT IMAGE ANALYSIS")
        print(f"    Source: {source_path}")
        print(f"    Size: {len(query_image):,} bytes")
        original_img = Image.open(io.BytesIO(query_image))
        print(f"    Original dimensions: {original_img.size[0]}x{original_img.size[1]}, Mode: {original_img.mode}")

        print(f"\n[2] PREPROCESSING")
        processed = preprocess_image(query_image)
        processed_img = Image.open(io.BytesIO(processed))
        print(f"    Processed: {processed_img.size[0]}x{processed_img.size[1]}, {len(processed):,} bytes")

        temp_path = save_temp(processed)
        print(f"    Temp file: {temp_path}")

        try:
            print(f"\n[3] FACE DETECTION (detector: {self.detector})")
            faces = DeepFace.extract_faces(img_path=str(temp_path), detector_backend=self.detector, enforce_detection=False)
            print(f"    Faces detected: {len(faces)}")
            for i, face in enumerate(faces):
                r = face.get("facial_area", {})
                print(f"    Face {i+1}: x={r.get('x',0)}, y={r.get('y',0)}, w={r.get('w',0)}, h={r.get('h',0)}, conf={face.get('confidence',0):.4f}")

            # Save debug image with face bounding boxes
            if faces:
                debug_img_path = save_face_debug_image(processed, faces)
                print(f"    Debug image: {debug_img_path}")

            if len(faces) == 0:
                print("    WARNING: No face detected!")
                raise NoFaceDetectedError()
            if len(faces) > 1:
                raise MultipleFacesError(len(faces))

            # Get query embedding for later use in finding matching face
            query_rep = DeepFace.represent(
                img_path=str(temp_path), model_name=self.model, detector_backend=self.detector,
                enforce_detection=False
            )
            query_embedding = query_rep[0]["embedding"] if query_rep else None

            print(f"\n[4] DATABASE CHECK")
            db_count = self._count_embeddings()
            print(f"    Total embeddings in DB: {db_count}")
            if db_count == 0:
                print("    WARNING: Database empty! Run 'python main.py register' first.")

            print(f"\n[5] SEARCH PARAMETERS")
            print(f"    Model: {self.model}, Detector: {self.detector}, Threshold: {self.threshold}, Limit: {limit}")

            print(f"\n[6] EXECUTING SEARCH...")
            results = DeepFace.search(
                img=str(temp_path), model_name=self.model, detector_backend=self.detector,
                distance_metric="cosine", database_type="postgres",
                connection_details=self._get_db_connection(), search_method="exact",
                similarity_search=True, k=limit, enforce_detection=False
            )

            print(f"\n[7] RAW RESULTS - type: {type(results)}, count: {len(results)}")
            matches, all_candidates = [], []
            for df_idx, df in enumerate(results):
                print(f"    Item {df_idx} type: {type(df)}")
                if hasattr(df, 'iterrows'):
                    print(f"    DataFrame {df_idx}: {len(df)} rows")
                    for _, row in df.iterrows():
                        dist = row.get("distance", 1.0)
                        identity = row.get("identity", row.get("img_name", ""))
                        all_candidates.append((identity, dist))
                        if dist <= self.threshold:
                            matches.append(SearchMatch(
                                image_path=identity, distance=dist, confidence=max(0, 1 - dist)
                            ))

            print(f"\n[8] CANDIDATE ANALYSIS (threshold={self.threshold})")
            if all_candidates:
                print(f"    Total candidates: {len(all_candidates)}")
                for i, (identity, dist) in enumerate(sorted(all_candidates, key=lambda x: x[1])[:10]):
                    status = "MATCH" if dist <= self.threshold else "REJECT"
                    # identity is now relative path from DB
                    print(f"    {i+1}. [{status}] dist={dist:.4f} conf={max(0,1-dist):.2%} - {identity}")
            else:
                print("    No candidates from DeepFace.search()")

            sorted_matches = sorted(matches, key=lambda x: x.distance)[:limit]
            print(f"\n[9] FINAL MATCHES: {len(sorted_matches)}")
            if not sorted_matches and all_candidates:
                best_dist = min(c[1] for c in all_candidates)
                print(f"    Best distance: {best_dist:.4f}, Threshold: {self.threshold}")
                if best_dist > self.threshold:
                    print(f"    HINT: Best candidate above threshold by {best_dist - self.threshold:.4f}")

            # Save debug images for matched results
            # Find the exact matching face by comparing embeddings
            if sorted_matches and query_embedding:
                print(f"\n[10] SAVING MATCH DEBUG IMAGES")
                for i, match in enumerate(sorted_matches):
                    try:
                        # Resolve relative path to absolute for file access
                        full_path = self.resolve_image_path(match.image_path)
                        # Find the face that matches the query embedding
                        matching_face = find_matching_face_in_image(
                            query_embedding, full_path, self.model, self.detector
                        )
                        if matching_face and matching_face.get("facial_area"):
                            debug_path = save_match_debug_image(
                                full_path, [matching_face], match.confidence
                            )
                            print(f"    {i+1}. {debug_path}")
                        else:
                            print(f"    {i+1}. Skipped (no matching face found)")
                    except Exception as e:
                        print(f"    {i+1}. Failed: {e}")

            print("=" * 60)
            return sorted_matches
        finally:
            temp_path.unlink(missing_ok=True)

    def _count_embeddings(self) -> int:
        import psycopg2
        try:
            conn = psycopg2.connect(**{k: self._get_db_connection()[k] for k in ['host', 'port', 'user', 'password', 'dbname']})
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM embeddings")
                return cur.fetchone()[0]
        except Exception:
            return -1
        finally:
            if 'conn' in locals():
                conn.close()
