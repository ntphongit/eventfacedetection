"""Image utilities."""
import io
import uuid
from pathlib import Path
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


def preprocess_image(content: bytes, max_dim: int = 1920) -> bytes:
    """Normalize image: convert to RGB, resize if needed."""
    img = Image.open(io.BytesIO(content))

    if img.mode != "RGB":
        img = img.convert("RGB")

    if max(img.size) > max_dim:
        ratio = max_dim / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=95)
    return out.getvalue()


def save_temp(content: bytes, temp_dir: str = "./tmp/uploads") -> Path:
    """Save to temp file, return path."""
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    path = Path(temp_dir) / f"{uuid.uuid4()}.jpg"
    path.write_bytes(content)
    return path


def save_face_debug_image(content: bytes, faces: list[dict], debug_dir: str = "./tmp/debug") -> Path:
    """Save image with face bounding boxes drawn for debugging.

    Args:
        content: Image bytes
        faces: List of face dicts with 'facial_area' containing x, y, w, h
        debug_dir: Directory to save debug image

    Returns:
        Path to saved debug image
    """
    from PIL import ImageDraw

    Path(debug_dir).mkdir(parents=True, exist_ok=True)
    img = Image.open(io.BytesIO(content))
    if img.mode != "RGB":
        img = img.convert("RGB")

    draw = ImageDraw.Draw(img)
    for i, face in enumerate(faces):
        area = face.get("facial_area", {})
        x, y, w, h = area.get("x", 0), area.get("y", 0), area.get("w", 0), area.get("h", 0)
        conf = face.get("confidence", 0)

        # Draw rectangle around face
        draw.rectangle([x, y, x + w, y + h], outline="green", width=3)
        # Draw label with face number and confidence
        label = f"Face {i+1}: {conf:.2%}"
        draw.text((x, y - 15), label, fill="green")

    path = Path(debug_dir) / f"face_detection_{uuid.uuid4().hex[:8]}.jpg"
    img.save(path, format="JPEG", quality=95)
    return path


def save_match_debug_image(
    image_path: str, faces: list[dict], match_confidence: float,
    debug_dir: str = "./tmp/matches"
) -> Path:
    """Save matched image with face bounding boxes and match confidence.

    Args:
        image_path: Path to original matched image
        faces: List of face dicts with 'facial_area' containing x, y, w, h
        match_confidence: Match confidence score (0-1)
        debug_dir: Directory to save debug image

    Returns:
        Path to saved debug image
    """
    from PIL import ImageDraw

    Path(debug_dir).mkdir(parents=True, exist_ok=True)
    img = Image.open(image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")

    draw = ImageDraw.Draw(img)
    for i, face in enumerate(faces):
        area = face.get("facial_area", {})
        x, y, w, h = area.get("x", 0), area.get("y", 0), area.get("w", 0), area.get("h", 0)

        # Draw rectangle around face
        draw.rectangle([x, y, x + w, y + h], outline="green", width=3)
        # Draw label with match confidence
        label = f"Match: {match_confidence:.2%}"
        draw.text((x, y - 15), label, fill="green")

    # Use original filename in debug output
    orig_name = Path(image_path).stem
    path = Path(debug_dir) / f"match_{orig_name}_{uuid.uuid4().hex[:6]}.jpg"
    img.save(path, format="JPEG", quality=95)
    return path
