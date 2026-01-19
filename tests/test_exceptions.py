"""Tests for custom exceptions."""
import pytest
from src.exceptions import (
    FaceDetectionError,
    NoFaceDetectedError,
    MultipleFacesError,
    UnsupportedFormatError
)


def test_face_detection_error():
    """Test base exception."""
    error = FaceDetectionError("Test error")
    assert str(error) == "Test error"


def test_no_face_detected_error():
    """Test no face detected exception."""
    error = NoFaceDetectedError()
    assert "No face detected" in str(error)
    assert "clear face" in str(error)


def test_multiple_faces_error():
    """Test multiple faces exception."""
    error = MultipleFacesError(3)
    assert "Multiple faces (3)" in str(error)
    assert error.count == 3


def test_unsupported_format_error():
    """Test unsupported format exception."""
    error = UnsupportedFormatError("gif")
    assert "Unsupported format: gif" in str(error)
    assert "JPEG, PNG, or HEIC" in str(error)
