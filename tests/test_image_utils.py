"""Tests for image utilities."""
import pytest
import io
from pathlib import Path
from PIL import Image


def test_preprocess_image_rgb():
    """Test preprocessing RGB image."""
    from src.utils.image_utils import preprocess_image

    # Create test RGB image
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    content = buf.getvalue()

    result = preprocess_image(content)

    assert result is not None
    assert len(result) > 0

    # Verify result is valid JPEG
    result_img = Image.open(io.BytesIO(result))
    assert result_img.mode == "RGB"


def test_preprocess_image_resize():
    """Test preprocessing large image."""
    from src.utils.image_utils import preprocess_image

    # Create large image
    img = Image.new("RGB", (3000, 2000), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    content = buf.getvalue()

    result = preprocess_image(content, max_dim=1920)

    result_img = Image.open(io.BytesIO(result))
    assert max(result_img.size) <= 1920


def test_preprocess_image_rgba_to_rgb():
    """Test converting RGBA to RGB."""
    from src.utils.image_utils import preprocess_image

    # Create RGBA image
    img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    content = buf.getvalue()

    result = preprocess_image(content)

    result_img = Image.open(io.BytesIO(result))
    assert result_img.mode == "RGB"


def test_save_temp():
    """Test saving temp file."""
    from src.utils.image_utils import save_temp
    import tempfile
    import shutil

    # Create test content
    img = Image.new("RGB", (100, 100), color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    content = buf.getvalue()

    # Use temp directory
    temp_dir = Path(tempfile.mkdtemp())
    try:
        path = save_temp(content, str(temp_dir))

        assert path.exists()
        assert path.suffix == ".jpg"
        assert path.read_bytes() == content
    finally:
        shutil.rmtree(temp_dir)
