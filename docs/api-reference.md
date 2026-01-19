# API Reference

## Base URL

```
http://localhost:8000
```

## Authentication

No authentication required (MVP). Internal use only.

## Response Format

All responses are JSON. Standard format:

```json
{
  "success": boolean,
  "data": object or array,
  "error": string (if success=false)
}
```

## Endpoints

### 1. Search for Matching Faces

Find photos matching a query face.

**Request**

```http
POST /search
Content-Type: multipart/form-data

Parameters:
- file (required): Binary image file (JPEG, PNG, HEIC)
- limit (optional): Max results to return (1-100, default 10)
```

**Example**

```bash
curl -X POST http://localhost:8000/search \
  -F "file=@query.jpg" \
  -F "limit=5"
```

**Successful Response (200 OK)**

```json
{
  "success": true,
  "matches": [
    {
      "image_path": "sukien_13012026/event_photos/may01/DSC06359.jpg",
      "confidence": 0.95,
      "distance": 0.05
    },
    {
      "image_path": "sukien_13012026/event_photos/may02/DSC00012.jpg",
      "confidence": 0.87,
      "distance": 0.13
    }
  ],
  "error": null
}
```

**No Face Detected**

```json
{
  "success": false,
  "matches": [],
  "error": "No face detected in image"
}
```

**Multiple Faces Detected**

```json
{
  "success": false,
  "matches": [],
  "error": "Multiple faces detected. Please provide image with single face"
}
```

**Error: Invalid File Type (400)**

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "detail": "File must be an image"
}
```

**Error: File Too Large (413)**

```http
HTTP/1.1 413 Payload Too Large
Content-Type: application/json

{
  "detail": "File too large (max 10MB)"
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| success | bool | Query succeeded (true) or failed (false) |
| matches | array | List of MatchResult objects |
| error | string | Error message if success=false |

**MatchResult Object**

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| image_path | string | - | Path to matched photo |
| confidence | float | 0-1 | Confidence score (0 = no match, 1 = perfect) |
| distance | float | 0-1 | Cosine distance (0 = identical, 1 = different) |

**Example with Python Requests**

```python
import requests

response = requests.post(
    "http://localhost:8000/search",
    files={"file": open("query.jpg", "rb")},
    params={"limit": 10}
)
data = response.json()

if data["success"]:
    for match in data["matches"]:
        print(f"{match['image_path']}: {match['confidence']:.1%}")
else:
    print(f"Error: {data['error']}")
```

---

### 2. Register Event Photos

Index photos to database for searching.

**Request**

```http
POST /register
Content-Type: application/x-www-form-urlencoded

Parameters:
- photos_dir (optional): Directory to register (default from config)
```

**Example**

```bash
curl -X POST http://localhost:8000/register \
  -d "photos_dir=./sukien_13012026/event_photos"
```

**Successful Response (200 OK)**

```json
{
  "success": true,
  "count": 42,
  "message": "Registered 42 photos"
}
```

**Error: Path Traversal Attempt (403)**

```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "detail": "Access to directory not allowed"
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| success | bool | Registration succeeded (true) or failed (false) |
| count | int | Number of photos successfully registered |
| message | string | Status message |

**Example with Python Requests**

```python
import requests

response = requests.post(
    "http://localhost:8000/register",
    data={"photos_dir": "./sukien_13012026/event_photos"}
)
data = response.json()

if data["success"]:
    print(f"Registered {data['count']} photos")
else:
    print(f"Error: {data['message']}")
```

---

### 3. Build Representations

Pre-compute embeddings for faster searches.

**Request**

```http
POST /build
```

**Example**

```bash
curl -X POST http://localhost:8000/build
```

**Response (200 OK)**

```json
{
  "message": "Built representations for 42 photos"
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| message | string | Status message with count |

**Example with Python Requests**

```python
import requests

response = requests.post("http://localhost:8000/build")
print(response.json()["message"])
```

---

### 4. Health Check

Check API health status.

**Request**

```http
GET /health
```

**Example**

```bash
curl http://localhost:8000/health
```

**Response (200 OK)**

```json
{
  "status": "ok"
}
```

**Response Fields**

| Field | Type | Description |
|-------|------|-------------|
| status | string | "ok" if healthy |

**Example with Python Requests**

```python
import requests

response = requests.get("http://localhost:8000/health")
if response.json()["status"] == "ok":
    print("API is healthy")
```

---

## Status Codes

| Code | Meaning | Scenario |
|------|---------|----------|
| 200 | OK | Successful request |
| 400 | Bad Request | Invalid file type or parameters |
| 403 | Forbidden | Path traversal attempt or access denied |
| 413 | Payload Too Large | File exceeds size limit |
| 500 | Internal Server Error | Unexpected server error |

## Configuration

### File Upload Limits

Default configuration in `config/config.yaml`:

```yaml
files:
  max_size_mb: 10
  allowed_formats: [jpeg, jpg, png, heic]
```

### CORS Configuration

Default allowed origins:

```yaml
api:
  allowed_origins:
    - http://localhost:3000
    - http://localhost:8000
```

To add more origins, edit `config/config.yaml` and restart API.

## Rate Limiting

No rate limiting in MVP. Future enhancement.

## Best Practices

### Search Optimization

1. **Query Image Quality**
   - Use clear, front-facing photos
   - Avoid: occlusions, poor lighting, extreme angles
   - Recommended: 640x480 or higher resolution

2. **Batch Operations**
   - Register all photos upfront with `/register`
   - Then perform searches with `/search`
   - Avoid repeated registrations

3. **Result Filtering**
   - Use confidence > 0.80 for strict matching
   - Use confidence > 0.60 for loose matching
   - Adjust threshold based on use case

### Performance Tips

1. **Pre-build Cache**
   - Call `/build` after registration for faster first search
   - Subsequent searches will be <500ms

2. **Limit Results**
   - Use `limit=5` for most use cases
   - Don't request `limit=100` unless necessary

3. **File Size**
   - Compress images before upload if >5MB
   - API will handle, but network faster with smaller files

## Examples

### JavaScript/Node.js

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function searchFace() {
  const form = new FormData();
  form.append('file', fs.createReadStream('query.jpg'));
  form.append('limit', 10);

  try {
    const response = await axios.post(
      'http://localhost:8000/search',
      form,
      { headers: form.getHeaders() }
    );

    const data = response.data;
    if (data.success) {
      data.matches.forEach((match, i) => {
        console.log(`${i+1}. ${match.image_path} (${(match.confidence*100).toFixed(1)}%)`);
      });
    } else {
      console.error(`Error: ${data.error}`);
    }
  } catch (error) {
    console.error(error.message);
  }
}

searchFace();
```

### cURL

```bash
# Search
curl -X POST http://localhost:8000/search \
  -F "file=@query.jpg" \
  -F "limit=10" | jq .

# Register
curl -X POST http://localhost:8000/register \
  -d "photos_dir=./sukien_13012026/event_photos" | jq .

# Build
curl -X POST http://localhost:8000/build | jq .

# Health
curl http://localhost:8000/health | jq .
```

### Python with Requests

```python
import requests
import json

BASE_URL = "http://localhost:8000"

def search(image_path, limit=10):
    """Search for matching faces."""
    with open(image_path, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/search",
            files={"file": f},
            params={"limit": limit}
        )
    return response.json()

def register(photos_dir):
    """Register photos directory."""
    response = requests.post(
        f"{BASE_URL}/register",
        data={"photos_dir": photos_dir}
    )
    return response.json()

def build():
    """Build representations."""
    response = requests.post(f"{BASE_URL}/build")
    return response.json()

def health():
    """Check health."""
    response = requests.get(f"{BASE_URL}/health")
    return response.json()

# Usage
if __name__ == "__main__":
    # Check health
    print(health())

    # Register photos
    result = register("./sukien_13012026/event_photos")
    print(f"Registered {result['count']} photos")

    # Search
    matches = search("query.jpg", limit=5)
    if matches["success"]:
        for m in matches["matches"]:
            print(f"{m['image_path']}: {m['confidence']:.1%}")
    else:
        print(f"Error: {matches['error']}")
```

## Troubleshooting

### Common Issues

**"No face detected"**
- Ensure image has a clear face
- Try different image: better lighting, no occlusions

**"Multiple faces detected"**
- Crop image to single face
- Use photo with only one person

**"File too large"**
- Compress image before upload
- Check file size: `ls -lh query.jpg`

**"Connection refused"**
- Check API is running: `curl http://localhost:8000/health`
- Verify port: `sudo lsof -i :8000`

**"404 Not Found"**
- Verify endpoint path (e.g., `/search` not `/Search`)
- Check API version in documentation

## See Also
- [Project Overview](./project-overview-pdr.md)
- [System Architecture](./system-architecture.md)
- [Codebase Summary](./codebase-summary.md)
