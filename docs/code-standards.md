# Code Standards & Development Guidelines

## Style & Conventions

### Python Style

**General:**
- Follow PEP 8 with focus on readability
- Use type hints for all functions (Python 3.10+)
- Max line length: 100 characters
- Use f-strings for string formatting
- Docstrings: Google-style format

**Naming Conventions:**
```python
# Classes: PascalCase
class FaceService:
    pass

# Functions/methods: snake_case
def validate_single_face(path: str) -> dict:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_FILE_SIZE_MB = 10

# Private members: _leading_underscore
def _get_db_connection(self) -> dict:
    pass

# Module-level constants
ALLOWED_FORMATS = {'.jpg', '.jpeg', '.png', '.heic'}
```

**Imports:**
```python
# Order: stdlib, third-party, local
import logging
from pathlib import Path
from dataclasses import dataclass

from fastapi import FastAPI, UploadFile
from deepface import DeepFace

from src.exceptions import NoFaceDetectedError
from src.utils.config_loader import get_config
```

### File Structure

**Module layout:**
```python
"""Module docstring explaining purpose."""

# Imports
import logging
from pathlib import Path

# Constants
THRESHOLD = 0.40
ALLOWED_FORMATS = {'.jpg', '.png'}

# Dataclasses/enums
@dataclass
class Result:
    """Represents result."""
    value: float

# Classes
class Service:
    """Main service class."""
    def __init__(self):
        pass

# Functions
def helper_function() -> str:
    """Utility function."""
    pass

# Main guard
if __name__ == "__main__":
    pass
```

## Code Patterns

### Service Layer Pattern

```python
class FaceService:
    """Thin wrapper around external libraries."""

    def __init__(self):
        self.config = get_config()
        self.model = self.config["deepface"]["model_name"]

    def public_method(self, param: str) -> dict:
        """Public API with validation."""
        self._validate_input(param)
        return self._internal_operation(param)

    def _internal_operation(self, param: str) -> dict:
        """Private implementation detail."""
        pass

    def _validate_input(self, param: str) -> None:
        """Validation helper."""
        if not param:
            raise ValueError("param cannot be empty")
```

**Principles:**
- Public methods are the interface
- Private methods (_prefix) are implementation details
- Validation upfront, fail fast
- Type hints on all signatures

### Error Handling Pattern

```python
# Define custom exceptions
class NoFaceDetectedError(Exception):
    """Raised when image has no face."""
    pass

# Use in services
try:
    faces = extract_faces(image_path)
    if len(faces) == 0:
        raise NoFaceDetectedError()
except NoFaceDetectedError as e:
    logger.warning(f"No face: {e}")
    return {"error": str(e)}  # Return error response

# Log with context
logger.error(f"Failed to process {image_path}: {e}", exc_info=True)
```

### Configuration Pattern

```python
# Load at startup
config = None

def load_config():
    """Load and cache config."""
    global config
    config = _load_yaml("config/config.yaml")

def get_config() -> dict:
    """Return cached config."""
    if config is None:
        load_config()
    return config

# In main application
# Call load_config() in main.py and cli entry point
```

### API Handler Pattern

```python
@app.post("/search", response_model=SearchResponse)
async def search(file: UploadFile = File(...)) -> SearchResponse:
    """Handle search request."""
    # 1. Validate input
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "File must be an image")

    # 2. Read with limits
    content = await file.read(MAX_SIZE + 1)
    if len(content) > MAX_SIZE:
        raise HTTPException(413, "File too large")

    # 3. Process (with error handling)
    try:
        result = service.search(content)
        return SearchResponse(success=True, matches=result)
    except NoFaceDetectedError as e:
        logger.warning(f"No face: {e}")
        return SearchResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return SearchResponse(success=False, error="Search failed")
```

**Pattern:**
1. Validate inputs early
2. Apply limits/security checks
3. Call service layer
4. Handle expected exceptions gracefully
5. Log unexpected errors

## Type Hints

**Use comprehensive type hints:**

```python
from typing import Optional, List, Dict

# Functions
def search(query: bytes, limit: int = 10) -> List[SearchMatch]:
    pass

# Optional parameters
def register(photos_dir: Optional[str] = None) -> int:
    pass

# Complex types
def process(data: Dict[str, List[float]]) -> Dict[str, any]:
    pass

# Union types (Python 3.10+)
def read_config(path: str | None = None) -> dict:
    pass

# Dataclass with types
@dataclass
class Match:
    image_path: str
    confidence: float
    distance: float
```

## Logging

**Use consistent logging:**

```python
import logging

logger = logging.getLogger(__name__)

# INFO: User-facing events
logger.info(f"Search returned {len(matches)} matches")

# WARNING: Expected errors handled gracefully
logger.warning(f"No face detected: {e}")

# ERROR: Unexpected errors
logger.error(f"Database connection failed: {e}", exc_info=True)
```

**Pattern:** Log level increases with severity:
- `debug`: Development details (rarely used in production)
- `info`: Business events (user actions, job completion)
- `warning`: Expected errors that are handled
- `error`: Unexpected failures that need attention

## Documentation

### Docstring Format

```python
def validate_single_face(image_path: str) -> dict:
    """Ensure exactly one face in image.

    Extracts faces from image and validates single face presence.
    Raises NoFaceDetectedError if 0 faces found.
    Raises MultipleFacesError if multiple faces found.

    Args:
        image_path: Path to image file.

    Returns:
        Face detection result dict.

    Raises:
        NoFaceDetectedError: No face found in image.
        MultipleFacesError: Multiple faces found.
    """
    faces = DeepFace.extract_faces(img_path=image_path)
    if len(faces) == 0:
        raise NoFaceDetectedError()
    if len(faces) > 1:
        raise MultipleFacesError(len(faces))
    return faces[0]
```

**Rules:**
- First line: Brief summary (one sentence)
- Blank line, then extended description
- `Args:` section with type and description
- `Returns:` section with type and description
- `Raises:` section with exceptions
- Examples for complex functions (optional)

### Class Docstrings

```python
class FaceService:
    """Thin wrapper around DeepFace API.

    Provides methods for face detection, embedding extraction,
    and similarity search against PostgreSQL database.

    Attributes:
        model: DeepFace model name (e.g., 'Facenet512').
        detector: Face detection backend.
        threshold: Cosine distance threshold for matching.
    """
```

## Testing Standards

### Test Organization

```
tests/
├── unit/
│   ├── test_face_service.py
│   └── test_image_utils.py
└── integration/
    ├── test_api_search.py
    └── test_api_register.py
```

### Test Pattern

```python
import pytest
from unittest.mock import Mock, patch

def test_validate_single_face_success():
    """Test validation passes with single face."""
    service = FaceService()
    with patch('src.services.face_service.DeepFace.extract_faces') as mock:
        mock.return_value = [{'face': 'data'}]
        result = service.validate_single_face('test.jpg')
        assert result == {'face': 'data'}

def test_validate_single_face_no_face():
    """Test validation raises when no face found."""
    service = FaceService()
    with patch('src.services.face_service.DeepFace.extract_faces') as mock:
        mock.return_value = []
        with pytest.raises(NoFaceDetectedError):
            service.validate_single_face('test.jpg')

@pytest.mark.asyncio
async def test_search_endpoint():
    """Test search endpoint with valid image."""
    client = TestClient(app)
    response = client.post(
        "/search",
        files={"file": ("test.jpg", b"fake_image", "image/jpeg")}
    )
    assert response.status_code == 200
    assert response.json()["success"] == True
```

**Patterns:**
- One test per behavior
- Descriptive names: `test_<function>_<scenario>`
- Arrange-Act-Assert pattern
- Mock external dependencies
- Use fixtures for common setup

## Security Guidelines

### Input Validation

```python
# Always validate file type
if not content_type.startswith("image/"):
    raise HTTPException(400, "File must be an image")

# Always check file size
max_size = 10 * 1024 * 1024
if len(content) > max_size:
    raise HTTPException(413, "File too large")

# Always validate paths (prevent traversal)
def validate_path(path: str, allowed_dirs: list[str]) -> bool:
    resolved = Path(path).resolve()
    for allowed in allowed_dirs:
        try:
            resolved.relative_to(Path(allowed).resolve())
            return True
        except ValueError:
            continue
    return False
```

### Sensitive Data

**Never log:**
```python
# DON'T
logger.info(f"DB password: {password}")

# DO
logger.info("Connected to database")
```

**Never commit:**
```
.env
.env.local
config/secrets.yaml
```

## Performance Guidelines

### File Handling

```python
# Use context managers for file operations
with open(image_path, 'rb') as f:
    content = f.read()

# Use Path for path operations
from pathlib import Path
path = Path(directory)
for image in path.rglob("*.jpg"):  # Efficient recursive glob
    process(image)
```

### Database Queries

```python
# Let DeepFace handle query batching
# Avoid N+1 queries

# Use connection pooling (PostgreSQL)
# Configure in Docker/env if using direct connections
```

## Code Review Checklist

- [ ] Type hints on all functions
- [ ] Docstrings for public methods
- [ ] Error handling with logging
- [ ] No hardcoded secrets
- [ ] Input validation on API handlers
- [ ] Path traversal checks
- [ ] Tests for new code
- [ ] No dead code
- [ ] Imports organized
- [ ] File under 200 lines (modularize if needed)

## Project Structure Maintenance

**Keep files focused:**
- `face_service.py`: Face operations only
- `main.py`: FastAPI app setup only
- `commands.py`: CLI wrappers only
- `config_loader.py`: Config loading only

**Modularize when growing:**
- File exceeds 200 LOC → Split into logical modules
- Multiple related services → Create service package
- Complex utilities → Break into separate modules

## See Also
- [Architecture & Design](./system-architecture.md)
- [Codebase Summary](./codebase-summary.md)
- [Project PDR](./project-overview-pdr.md)
