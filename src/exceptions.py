"""Custom exceptions for face detection."""


class FaceDetectionError(Exception):
    """Base exception."""
    pass


class NoFaceDetectedError(FaceDetectionError):
    def __init__(self):
        super().__init__("No face detected. Please upload image with clear face.")


class MultipleFacesError(FaceDetectionError):
    def __init__(self, count: int):
        super().__init__(f"Multiple faces ({count}). Upload image with one face.")
        self.count = count


class UnsupportedFormatError(FaceDetectionError):
    def __init__(self, fmt: str):
        super().__init__(f"Unsupported format: {fmt}. Use JPEG, PNG, or HEIC.")
