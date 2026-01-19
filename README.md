# Event Face Detection MVP

AI-powered face detection and recognition system for event photos using DeepFace and PostgreSQL.

## Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- 10GB+ disk space (for models)

### Installation

```bash
# Clone and install
git clone <repo>
cd eventfacedetection
pip install -r requirements.txt

# Start PostgreSQL
docker-compose up -d postgres

# Configure environment
cp .env.example .env
# Edit .env with your database credentials
```

### Usage

#### CLI: Register Photos
```bash
python main.py register --photos ./sukien_13012026/event_photos
```

#### CLI: Search for Matching Faces
```bash
python main.py search "./sukien_13012026/guest_photos/Nguyen_Thanh_Phong/Phong Nguyen.png"
```

#### CLI: Pre-build Representations
```bash
python main.py build
```

#### API: Start Server
```bash
uvicorn src.api.main:app --reload
```

**API Endpoints:**
- `GET /health` - Health check
- `POST /search` - Search for matching faces (multipart file upload)
- `POST /register` - Register event photos
- `POST /build` - Pre-build face representations

## Architecture

```
src/
├── api/           # FastAPI application & schemas
├── cli/           # Click CLI commands
├── services/      # FaceService (DeepFace wrapper)
└── utils/         # Config loader & image utilities
```

**Flow:**
1. Image → Preprocess → Face validation (single face required)
2. Extract embeddings via DeepFace (Facenet512)
3. Search PostgreSQL using cosine distance
4. Return matches sorted by confidence

## Configuration

Edit `config/config.yaml`:

```yaml
database:
  host: ${DB_HOST:-localhost}
  port: ${DB_PORT:-5432}
  user: ${DB_USER:-deepface}
  password: ${DB_PASSWORD:-deepface}
  database: ${DB_NAME:-deepface_db}

deepface:
  model_name: Facenet512
  detector_backend: retinaface
  distance_metric: cosine
  threshold: 0.40  # Confidence threshold

storage:
  event_photos: ./sukien_13012026/event_photos
  allowed_directories:
    - ./sukien_13012026

files:
  max_size_mb: 10
  allowed_formats: [jpeg, jpg, png, heic]
```

## Key Components

### FaceService
Wrapper around DeepFace API:
- `validate_single_face()` - Ensure exactly one face in image
- `search()` - Find matching faces with confidence scores
- `register_event_photos()` - Index photos to PostgreSQL
- `build_representations()` - Pre-compute embeddings

### Schemas
- `SearchResponse` - Match results with confidence
- `RegisterResponse` - Registration status
- `HealthResponse` - API health status

### CLI Commands
- `register` - Index photos to database
- `build` - Pre-build representations cache
- `search` - Search query image against database
- `config` - Display current configuration

## Error Handling

**NoFaceDetectedError** - No face found in image
**MultipleFacesError** - Multiple faces detected (single face required)
**HTTPException** - API validation errors (file type, size)

## Testing

```bash
pytest -v
pytest --cov=src/
```

## Performance Notes

- Facenet512: Accurate but slower (~2-5s per image)
- RetinaFace: Fast face detection
- PostgreSQL ANN search: Efficient for large datasets
- Threshold 0.40: Strict matching (adjust for recall vs precision)

## Security

- Path traversal protection in API (whitelist validation)
- File size limits (10MB default)
- Image format validation
- CORS configuration per config

## See Also
- [Architecture & Code Standards](./docs/system-architecture.md)
- [API Documentation](./docs/api-docs.md)
- [Codebase Summary](./docs/codebase-summary.md)
