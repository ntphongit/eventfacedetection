# Event Face Detection MVP - Project Overview & PDR

## Executive Summary

**Event Face Detection** is an AI-powered system for searching event photos by face. Users upload a query image, and the system returns matching attendees from the event photo database with confidence scores.

**Primary Use Case:** Event organizers need to quickly identify who attended an event by providing a photo of a guest.

**MVP Scope:** CLI + REST API for face search against pre-indexed event photos.

## Product Requirements Document (PDR)

### Core Functional Requirements

#### FR-1: Face Search
- User uploads image containing face
- System extracts facial embedding
- System searches against PostgreSQL index
- System returns up to N matching photos with confidence
- **Acceptance Criteria:**
  - Search completes in <10 seconds
  - Returns matches ranked by confidence (0-100%)
  - Handles single-face images only
  - Returns empty list if no matches found

#### FR-2: Photo Registration
- User specifies directory containing event photos
- System extracts face embeddings from all photos
- System stores embeddings in PostgreSQL with image paths
- System returns count of successfully registered photos
- **Acceptance Criteria:**
  - Registers all valid image formats (JPEG, PNG, HEIC)
  - Handles single-face images only
  - Skips multi-face photos with warning
  - Transactional: all-or-nothing

#### FR-3: Pre-build Cache
- User can pre-compute face embeddings before searches
- System builds and caches representations
- Improves search latency on first query
- **Acceptance Criteria:**
  - Completes without user interaction
  - Returns count of processed photos
  - Logs warnings for skipped images

#### FR-4: Health Check
- API provides health endpoint for monitoring
- **Acceptance Criteria:**
  - Responds with 200 OK
  - Includes status message

### Non-Functional Requirements

#### NFR-1: Performance
- **Search latency:** <10 seconds per query (including DeepFace operations)
- **Registration:** Handle 1000+ photos per batch
- **Database:** Sub-100ms query time for similarity search
- **Memory:** Efficient temp file handling (no disk bloat)

#### NFR-2: Scalability
- Database: PostgreSQL with ANN indexes
- API: Stateless (horizontally scalable)
- CLI: Single-instance for batch operations
- File storage: Local or cloud filesystem

#### NFR-3: Reliability
- Graceful error handling for invalid images
- Clear error messages for users
- Logging for debugging
- Atomic operations (no partial registrations)

#### NFR-4: Security
- **Path Traversal Protection:** Whitelist allowed directories
- **File Validation:** Type and size checks
- **CORS:** Configurable per environment
- **No Secrets:** Environment variables for credentials
- **Temporary Files:** Auto-cleanup after processing

#### NFR-5: Usability
- Intuitive CLI commands with help
- RESTful API design
- Comprehensive logging
- Configuration via YAML (with env overrides)

### API Specification

#### Endpoint: Search

```
POST /search
Content-Type: multipart/form-data

Request:
- file: Binary image (JPEG, PNG, HEIC, required)
- limit: Integer 1-100 (optional, default 10)

Response (200 OK):
{
  "success": true,
  "matches": [
    {
      "image_path": "sukien_13012026/event_photos/may01/DSC06359.jpg",
      "confidence": 0.95,  # 0-100%
      "distance": 0.05     # 0-1, lower = more similar
    }
  ],
  "error": null
}

Response (No faces):
{
  "success": false,
  "matches": [],
  "error": "No face detected in image"
}

Response (Multiple faces):
{
  "success": false,
  "matches": [],
  "error": "Multiple faces detected. Please provide image with single face"
}

Response (File too large):
Status 413, "File too large (max 10MB)"
```

#### Endpoint: Register

```
POST /register
Content-Type: application/x-www-form-urlencoded

Request:
- photos_dir: String (optional, uses default if not provided)

Response (200 OK):
{
  "success": true,
  "count": 42,
  "message": "Registered 42 photos"
}

Response (Access denied):
Status 403, "Access to directory not allowed"
```

#### Endpoint: Build

```
POST /build

Response (200 OK):
{
  "message": "Built representations for 42 photos"
}
```

#### Endpoint: Health

```
GET /health

Response (200 OK):
{
  "status": "ok"
}
```

### CLI Specification

#### Command: register
```bash
python main.py register [--photos PATH]
# Output: "Registering photos from: {PATH}"
#         "Registered 42 photos."
```

#### Command: search
```bash
python main.py search IMAGE_PATH [--limit N] [--db-path PATH]
# Output: "Found 3 matches:\n"
#         "1. path/to/photo1.jpg\n   Confidence: 95%\n"
#         "2. path/to/photo2.jpg\n   Confidence: 87%"
```

#### Command: build
```bash
python main.py build [--db-path PATH]
# Output: "Building representations for: {PATH}"
#         "Processed 42 photos. Cache ready."
```

#### Command: config
```bash
python main.py config
# Output: YAML dump of current configuration
```

### Data Model

#### SearchMatch (Python Dataclass)
```python
@dataclass
class SearchMatch:
    image_path: str          # Path to matched photo
    distance: float          # 0-1, cosine distance
    confidence: float        # 0-1, (1 - distance)
```

#### Pydantic Models (API)
```python
class MatchResult(BaseModel):
    image_path: str
    confidence: float
    distance: float

class SearchResponse(BaseModel):
    success: bool
    matches: List[MatchResult] = []
    error: Optional[str] = None

class RegisterResponse(BaseModel):
    success: bool
    count: int
    message: str

class HealthResponse(BaseModel):
    status: str
```

### Configuration

#### Environment Variables
```
DB_HOST=localhost
DB_PORT=5432
DB_USER=deepface
DB_PASSWORD=deepface
DB_NAME=deepface_db
```

#### YAML Configuration (config/config.yaml)
```yaml
database:
  host, port, user, password, database

deepface:
  model_name: Facenet512              # 512-dim embeddings
  detector_backend: retinaface        # Fast, accurate detection
  distance_metric: cosine             # Standard metric
  threshold: 0.40                     # Confidence threshold

storage:
  event_photos: ./sukien_13012026/event_photos
  allowed_directories: [./sukien_13012026]

api:
  host: 0.0.0.0
  port: 8000
  allowed_origins: [http://localhost:3000]

files:
  max_size_mb: 10
  allowed_formats: [jpeg, jpg, png, heic]
```

### Error Handling

| Error | Cause | Response |
|-------|-------|----------|
| NoFaceDetectedError | Image has 0 faces | 200 + error message |
| MultipleFacesError | Image has >1 face | 200 + error message |
| Invalid content-type | File not image | 400 Bad Request |
| File too large | Exceeds limit | 413 Payload Too Large |
| Path traversal attempt | Directory not whitelisted | 403 Forbidden |
| DB error | Connection/query failure | 500 + error message |

## Architecture Decisions

### Why DeepFace + PostgreSQL?

**DeepFace:**
- Open-source, well-maintained
- Multiple models (Facenet512 preferred for accuracy)
- Built-in PostgreSQL support
- Good performance/accuracy tradeoff

**PostgreSQL:**
- ANN (Approximate Nearest Neighbors) indexes for fast similarity search
- ACID transactions for reliability
- JSONB support for flexible schema
- Industry-standard

### Why Facenet512?

- **Accuracy:** 99.7% on LFW benchmark
- **Embeddings:** 512-dimensional, good tradeoff between precision and speed
- **Speed:** ~2-3s per image on CPU
- **Stability:** Consistent across DeepFace versions

### Why Cosine Distance?

- **Semantic:** Works well with normalized embeddings
- **Efficiency:** Fast to compute
- **Threshold:** Well-studied (0.40 = ~95% accuracy at default settings)
- **Interpretability:** 0 = identical, 1 = completely different

### Single Face Requirement

**Rationale:**
- Simplifies matching logic
- Prevents ambiguous results
- MVP scope limitation
- Can be relaxed in future

## Future Enhancements

### Phase 2: Advanced Features
- [ ] Multi-face support (return results per face)
- [ ] Batch search (multiple query images)
- [ ] Tag/label management
- [ ] Search history/analytics
- [ ] GPU acceleration
- [ ] Web UI dashboard

### Phase 3: Production Hardening
- [ ] Authentication/authorization
- [ ] Audit logging
- [ ] Rate limiting
- [ ] Database backup/restore
- [ ] Horizontal scaling
- [ ] CDN for photo delivery

### Phase 4: Intelligence
- [ ] Soft clustering (group similar faces)
- [ ] Anomaly detection (identify non-attendees)
- [ ] Demographics extraction
- [ ] Photo quality scoring
- [ ] Duplicate detection

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Search latency | <10s | API response time |
| Search accuracy | >90% | Manual validation |
| Registration throughput | >100 photos/min | Benchmark |
| Uptime | >99% | Monitoring |
| Error rate | <1% | Logs/monitoring |
| User satisfaction | >4/5 | Feedback survey |

## Constraints & Assumptions

### Constraints
- Single-face images only (MVP)
- Max 10MB file upload
- PostgreSQL for storage (not cloud DB)
- Local file storage (not S3)
- No authentication (internal use)

### Assumptions
- Event photos are JPEG/PNG/HEIC format
- Photos contain clear faces
- Database contains 1000-50000 photos
- Search latency <10s is acceptable
- Users have local network access to API
- Photos remain stable (not deleted after registration)

## Testing Strategy

### Unit Tests
- Service layer methods
- Utility functions
- Configuration loading

### Integration Tests
- API endpoints with mock DeepFace
- Database operations
- File handling

### End-to-End Tests
- Full registration workflow
- Full search workflow
- Error scenarios

## Deployment

### Development
```bash
docker-compose up -d postgres
uvicorn src.api.main:app --reload
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
gunicorn src.api.main:app -w 4
```

## Maintenance & Operations

### Monitoring
- API response times
- Database query times
- Error rates
- Storage usage

### Backups
- PostgreSQL: Daily backups
- Photo storage: Version control/snapshots

### Updates
- DeepFace upgrades quarterly
- TensorFlow security patches as needed
- PostgreSQL upgrades yearly

## Project Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 0: MVP Core | 1-2 weeks | Completed |
| Phase 1: Integration | 1 week | In Progress |
| Phase 2: Advanced Features | 2-3 weeks | Planned |
| Phase 3: Production | 2-3 weeks | Planned |

## Team & Roles

- **Backend Developer**: Implementation, testing
- **DevOps**: Deployment, monitoring
- **Product Manager**: Requirements, prioritization

## See Also
- [System Architecture](./system-architecture.md)
- [Code Standards](./code-standards.md)
- [Codebase Summary](./codebase-summary.md)
