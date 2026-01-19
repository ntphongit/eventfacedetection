# Event Face Detection - Codebase Summary

## Project Overview

**Event Face Detection MVP** is a face recognition system designed for event photo management. It leverages DeepFace for face detection/embedding and PostgreSQL for efficient similarity search.

**Core Purpose:** Index event photos, then search them by query image to find matching attendees.

**Tech Stack:**
- Python 3.10+
- FastAPI (REST API)
- Click (CLI)
- DeepFace (face embeddings)
- PostgreSQL (embedding storage + ANN search)
- Pillow/Pillow-HEIF (image processing)

## Directory Structure

```
.
├── config/
│   └── config.yaml              # DeepFace, DB, API, storage config
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI app, CORS, endpoints
│   │   └── schemas.py           # Pydantic models (search, register, health)
│   ├── cli/
│   │   └── commands.py          # Click commands (register, build, search, config)
│   ├── services/
│   │   └── face_service.py      # FaceService wrapper (DeepFace + PostgreSQL)
│   ├── utils/
│   │   ├── config_loader.py     # Load/validate YAML config with env vars
│   │   └── image_utils.py       # Image preprocessing, temp file handling
│   └── exceptions.py            # NoFaceDetectedError, MultipleFacesError
├── docker-compose.yml           # PostgreSQL service
├── requirements.txt             # Dependencies
├── main.py                      # CLI entry point
└── docs/
    ├── codebase-summary.md      # This file
    ├── system-architecture.md   # Architecture & data flow
    ├── code-standards.md        # Code style & patterns
    └── project-overview-pdr.md  # Requirements & PDR
```

## Key Components

### Config Module (`config/config.yaml`)

Centralizes configuration with environment variable overrides:

```yaml
database:         # PostgreSQL connection
deepface:         # Model, detector, threshold settings
storage:          # Event photo paths, allowed directories
api:              # Host, port, CORS allowed_origins
files:            # Upload limits, format whitelist
```

**Loading:** Config auto-loads in `api/main.py` and `cli/commands.py` via `load_config()`.

### FaceService (`src/services/face_service.py`)

Core business logic layer:

| Method | Purpose |
|--------|---------|
| `validate_single_face()` | Enforce single face constraint |
| `search(bytes, limit)` | Query image → match list |
| `register_event_photos()` | Index directory to PostgreSQL |
| `build_representations()` | Alias for registration |
| `_get_db_connection()` | PostgreSQL credentials from config |

**Search Flow:**
1. Preprocess image → Extract face
2. Validate single face (raise if 0 or >1)
3. DeepFace.search() with PostgreSQL backend
4. Convert DataFrame results to SearchMatch objects
5. Sort by distance, return top-N

**Registration Flow:**
1. DeepFace.register() scans directory
2. Extracts faces, computes embeddings
3. Stores in PostgreSQL with image path
4. Count registered images

### API (`src/api/main.py`)

FastAPI application with 4 endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check (returns 200) |
| `/search` | POST | Upload image, get matches |
| `/register` | POST | Index photos from directory |
| `/build` | POST | Trigger representation building |

**Security:**
- File type validation (image/* only)
- File size limit (10MB default, configurable)
- Path traversal protection: `validate_path()` checks against allowed_directories whitelist
- CORS middleware configured from config

**Response Models:**
- `SearchResponse`: success, matches (list), error (optional)
- `RegisterResponse`: success, count, message
- `HealthResponse`: status

### CLI (`src/cli/commands.py`)

Click-based command group:

```bash
python main.py register [--photos DIR]
python main.py build [--db-path DIR]
python main.py search IMAGE_PATH [--limit N] [--db-path DIR]
python main.py config
```

Each command instantiates FaceService and executes operations.

### Utilities

**config_loader.py:**
- `get_config()` - Returns loaded config dict
- `load_config()` - Loads YAML with env var interpolation

**image_utils.py:**
- `preprocess_image(bytes)` - Resize, normalize
- `save_temp(PIL.Image)` - Save to temp file for DeepFace

### Schemas (`src/api/schemas.py`)

Pydantic models for API:
- `MatchResult`: image_path, confidence, distance
- `SearchResponse`: success, matches, error
- `RegisterResponse`: success, count, message
- `HealthResponse`: status

### Exceptions (`src/exceptions.py`)

Custom exceptions:
- `NoFaceDetectedError` - Image has no face
- `MultipleFacesError` - Image has multiple faces

## Data Flow

### Search Flow
```
User Query Image
    ↓
[Preprocess] → Resize, normalize
    ↓
[Validate] → Exactly 1 face?
    ↓
[DeepFace Extract] → Get embeddings
    ↓
[PostgreSQL Search] → Cosine distance ANN
    ↓
[Sort & Return] → Top-N matches with confidence
```

### Registration Flow
```
Event Photos Directory
    ↓
[DeepFace.register()] → Batch extract + embed
    ↓
[PostgreSQL Insert] → Store embeddings + metadata
    ↓
[Return Count] → Photos registered
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| deepface | >=0.0.93 | Face detection/embedding |
| tensorflow | >=2.15.0 | Deep learning (DeepFace backend) |
| fastapi | >=0.109.0 | REST API framework |
| uvicorn | >=0.27.0 | ASGI server |
| click | >=8.1.0 | CLI framework |
| pillow | >=10.0.0 | Image processing |
| pillow-heif | >=0.15.0 | HEIC format support |
| pyyaml | >=6.0.0 | Config parsing |
| psycopg2-binary | >=2.9.0 | PostgreSQL adapter |
| pytest | >=7.0.0 | Testing framework |

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Face detection | ~1-2s | RetinaFace backend |
| Embedding extraction | ~1-3s | Facenet512 model |
| PostgreSQL search | <100ms | ANN-based, depends on DB size |
| Image preprocess | <100ms | Resize, normalize |

**Bottleneck:** DeepFace operations (2-5s per image). Consider:
- Batch processing for registration
- GPU acceleration if available
- Pre-built representations cache

## Configuration Files

**config/config.yaml:**
```yaml
deepface.threshold: 0.40      # Cosine distance threshold (lower = stricter)
storage.event_photos          # Default search directory
files.max_size_mb: 10         # API upload limit
api.allowed_origins           # CORS whitelist
```

**Environment Variables (overrides config):**
```
DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
```

## Error Handling Strategy

| Scenario | Response | Code |
|----------|----------|------|
| No face in image | `NoFaceDetectedError` | CLI: stderr, API: 200 with error field |
| Multiple faces | `MultipleFacesError` | CLI: stderr, API: 200 with error field |
| File too large | HTTPException | 413 |
| Invalid image type | HTTPException | 400 |
| Path traversal attempt | HTTPException | 403 |
| DB connection error | Exception logged, graceful failure | 500 error message |

## Code Patterns

**Service Layer:** FaceService encapsulates DeepFace operations
**Config Injection:** YAML config loaded at startup, passed to services
**Temporary Files:** Images saved to temp, cleaned up after processing
**Type Hints:** Full Python 3.10+ type annotations
**Error Propagation:** Exceptions logged, returned in API responses

## Testing

Test structure mirrors `src/`:
- Unit tests for services, utilities
- Integration tests for API endpoints
- Mock DeepFace for deterministic testing

Run: `pytest -v --cov=src/`

## Deployment

**Docker:** PostgreSQL in docker-compose.yml
**API:** `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
**CLI:** `python main.py [command]`

## See Also

- [System Architecture](./system-architecture.md) - Detailed design
- [Code Standards](./code-standards.md) - Style guide & patterns
- [Project PDR](./project-overview-pdr.md) - Requirements & scope
