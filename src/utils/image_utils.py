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
