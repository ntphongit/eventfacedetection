# System Architecture & Design

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Event Face Detection                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐                      ┌──────────────┐          │
│  │   CLI        │                      │   FastAPI    │          │
│  │  (Click)     │                      │   REST API   │          │
│  └──────┬───────┘                      └──────┬───────┘          │
│         │                                     │                  │
│         └──────────────────┬──────────────────┘                  │
│                            │                                     │
│                    ┌───────▼────────┐                            │
│                    │ FaceService    │                            │
│                    │ (DeepFace API) │                            │
│                    └───────┬────────┘                            │
│                            │                                     │
│         ┌──────────────────┼──────────────────┐                  │
│         │                  │                  │                  │
│    ┌────▼─────┐      ┌─────▼──────┐   ┌──────▼──┐               │
│    │ DeepFace │      │ PostgreSQL │   │ Config  │               │
│    │  Models  │      │ Database   │   │  YAML   │               │
│    │(Facenet  │      │ (ANN Search)   │         │               │
│    │512)      │      └────────────┘   └─────────┘               │
│    └──────────┘                                                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Interface Layer

#### CLI (`src/cli/commands.py`)
- **Register**: Batch index photos → `service.register_event_photos()`
- **Search**: Query image → `service.search()`
- **Build**: Pre-compute embeddings → `service.build_representations()`
- **Config**: Display current configuration

#### REST API (`src/api/main.py`)
- **POST /search**: Multipart file upload → face search
- **POST /register**: Directory registration
- **POST /build**: Trigger representation building
- **GET /health**: Status check
- **Security**: CORS, path validation, file size limits

### 2. Business Logic Layer

#### FaceService (`src/services/face_service.py`)

**Core Methods:**

| Method | Input | Output | Logic |
|--------|-------|--------|-------|
| `validate_single_face(path)` | Image path | Face dict | Extract faces, enforce count=1 |
| `search(bytes, limit)` | Image bytes | List[SearchMatch] | Extract embedding, search DB, sort by distance |
| `register_event_photos(dir)` | Directory path | count | Batch register, return file count |
| `build_representations(dir)` | Directory path | count | Alias for register |

**Key Implementation Details:**

- Uses DeepFace.search() with PostgreSQL backend
- Distance metric: cosine (0 = identical, 1 = different)
- Threshold 0.40: Confidence = max(0, 1 - distance)
- ANN search: Approximate nearest neighbors for speed
- Temp file cleanup: Ensures no disk bloat

### 3. Data Layer

#### PostgreSQL

**Schema (auto-created by DeepFace):**
```sql
-- DeepFace manages this table
representations (
  id BIGSERIAL PRIMARY KEY,
  img_name VARCHAR,           -- Image file path
  embedding FLOAT8[],         -- 512-dim Facenet512 vector
  embedding_model VARCHAR,    -- "Facenet512"
  detection_model VARCHAR,    -- "retinaface"
  distance_metric VARCHAR,    -- "cosine"
  hash VARCHAR UNIQUE         -- Image hash
)

-- ANN index for cosine search
CREATE INDEX idx_embeddings_cosine
  ON representations USING ivfflat (embedding vector_cosine_ops);
```

**Queries:**
- `INSERT`: DeepFace.register() populates table
- `SELECT`: DeepFace.search() uses ANN for similarity search
- Distance calculation: Cosine distance between query and stored vectors

#### Configuration (`config/config.yaml`)

Structured YAML with environment variable overrides:

```yaml
database:
  host: ${DB_HOST:-localhost}      # ENV override or default
  port: ${DB_PORT:-5432}
  user: ${DB_USER:-deepface}
  password: ${DB_PASSWORD:-deepface}
  database: ${DB_NAME:-deepface_db}

deepface:
  model_name: Facenet512            # 512-dim embeddings
  detector_backend: retinaface      # Face detection model
  distance_metric: cosine           # Similarity measure
  threshold: 0.40                   # Match threshold

storage:
  event_photos: ./sukien_13012026/event_photos
  allowed_directories:              # Whitelist for API
    - ./sukien_13012026

api:
  host: 0.0.0.0
  port: 8000
  allowed_origins:                  # CORS whitelist
    - http://localhost:3000

files:
  max_size_mb: 10
  allowed_formats: [jpeg, jpg, png, heic]
```

### 4. Utility Layer

#### config_loader.py
- Loads YAML with env var substitution
- Validates structure
- Caches config in memory

#### image_utils.py
- `preprocess_image(bytes)`: Resize, normalize
- `save_temp(PIL.Image)`: Temp file management

## Data Flow Diagrams

### Search Flow

```
User                    CLI/API              FaceService          DeepFace            PostgreSQL
 │                        │                      │                   │                    │
 │─ image_path ────────→  │                      │                   │                    │
 │                        │─ bytes ────────────→ │                   │                    │
 │                        │                      │─ preprocess ──→   │                    │
 │                        │                      │ validate_single    │                    │
 │                        │                      │                   │                    │
 │                        │                      │─ search ─────────→ │                    │
 │                        │                      │ (DeepFace.search)  │─ ANN query ──────→ │
 │                        │                      │                   │←─ results ────────│
 │                        │                      │←─ results ────── │                    │
 │                        │←─ matches ────────── │                   │                    │
 │←─ results ──────────── │                      │                   │                    │
```

**Steps:**
1. Image preprocessing (resize, normalize)
2. Face extraction & validation (enforce single face)
3. DeepFace embedding extraction
4. PostgreSQL ANN search (cosine distance)
5. Results sorted by confidence, return top-N

### Registration Flow

```
Photos Directory       FaceService          DeepFace            PostgreSQL
     │                    │                   │                    │
     │─ dir_path ────────→ │                   │                    │
     │                     │─ register ──────→ │                    │
     │                     │ (batch)           │─ extract ─────────→ │
     │                     │                   │ embeddings          │
     │                     │                   │  (Facenet512)       │
     │                     │                   │─ insert ──────────→ │
     │                     │                   │ representations    │
     │                     │←─ count ─────────│ ←─ done ────────── │
     │←─ count ─────────── │                   │                    │
```

## API Response Models

### SearchResponse
```json
{
  "success": true,
  "matches": [
    {
      "image_path": "sukien_13012026/event_photos/may01/DSC06359.jpg",
      "confidence": 0.95,
      "distance": 0.05
    }
  ],
  "error": null
}
```

### RegisterResponse
```json
{
  "success": true,
  "count": 42,
  "message": "Registered 42 photos"
}
```

### HealthResponse
```json
{
  "status": "ok"
}
```

## Error Handling Architecture

**Exception Hierarchy:**

```
Exception
├── NoFaceDetectedError
│   └── Raised by: validate_single_face()
│   └── Handled by: API (200 + error), CLI (stderr)
├── MultipleFacesError
│   └── Raised by: validate_single_face()
│   └── Handled by: API (200 + error), CLI (stderr)
└── HTTPException (FastAPI)
    ├── 400: Invalid image type
    ├── 403: Path traversal attempt
    ├── 413: File too large
    └── 500: Unexpected error
```

**Error Response Strategy:**
- CLI: Print to stderr, exit with non-zero code
- API: Always return 200 with success=false in JSON (allows client error handling)

## Security Architecture

### Path Traversal Protection
```python
def validate_path(path: str, allowed_dirs: list[str]) -> bool:
    """Verify path is within allowed_directories whitelist."""
    resolved = Path(path).resolve()
    for allowed in allowed_dirs:
        allowed_resolved = Path(allowed).resolve()
        try:
            resolved.relative_to(allowed_resolved)  # Raises ValueError if outside
            return True
        except ValueError:
            continue
    return False
```

### File Validation
- **Type**: Content-type must start with `image/`
- **Size**: Max 10MB (configurable)
- **Format**: Whitelist JPEG, PNG, HEIC

### CORS Configuration
- Origins from config (`allowed_origins`)
- Methods: GET, POST only
- Headers: Unrestricted

## Performance Considerations

### Bottlenecks
| Operation | Time | Mitigation |
|-----------|------|-----------|
| Face detection | 1-2s | Batch processing, GPU |
| Embedding extraction | 1-3s | Pre-compute, cache |
| Image preprocessing | <100ms | Optimize resize params |
| Database search | <100ms | ANN indexing, DB tuning |

### Optimization Strategies
1. **Batch Registration**: Process multiple images in one DeepFace call
2. **Caching**: Pre-build and cache embeddings
3. **GPU Acceleration**: TensorFlow GPU backend (if available)
4. **Connection Pooling**: PostgreSQL connection reuse
5. **Index Optimization**: Maintain ANN indexes

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│      Production Environment              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────────┐                   │
│  │  Uvicorn Server  │                   │
│  │  (API + CLI)     │                   │
│  └────────┬─────────┘                   │
│           │                             │
│           │ (port 8000)                 │
│  ┌────────▼──────────────────┐          │
│  │   External Clients         │          │
│  │   (React, curl, etc.)      │          │
│  └────────────────────────────┘          │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │   PostgreSQL Container            │   │
│  │   (docker-compose)                │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │   Event Photos Storage            │   │
│  │   (./sukien_13012026/)            │   │
│  └──────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

**Deployment Steps:**
1. Start PostgreSQL: `docker-compose up -d postgres`
2. Start API: `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
3. Register photos: `python main.py register`
4. Query via CLI or API

## See Also
- [Codebase Summary](./codebase-summary.md) - Module breakdown
- [Code Standards](./code-standards.md) - Development patterns
- [Project PDR](./project-overview-pdr.md) - Requirements
