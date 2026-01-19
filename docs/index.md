# Event Face Detection Documentation Index

Welcome! This is the central hub for Event Face Detection MVP documentation. Choose your starting point based on your role.

## Quick Navigation

### For Everyone

- **[README](../README.md)** - 5-minute overview and quick start
- **[Project Overview & PDR](./project-overview-pdr.md)** - What we're building and why

### For Developers

- **[Codebase Summary](./codebase-summary.md)** - Module breakdown and architecture overview
- **[System Architecture](./system-architecture.md)** - Technical design and data flows
- **[Code Standards](./code-standards.md)** - Development guidelines and patterns

### For Integration

- **[API Reference](./api-reference.md)** - Complete endpoint documentation with examples
- **[Development Roadmap](./development-roadmap.md)** - Project phases and timeline

---

## Documentation by Role

### New Developer

1. Read [README](../README.md) (5 min)
2. Run quick start setup
3. Read [Codebase Summary](./codebase-summary.md) (15 min)
4. Review [Code Standards](./code-standards.md) (15 min)
5. Start coding!

**Estimated time:** ~1 hour

### Backend Engineer

1. Review [System Architecture](./system-architecture.md) for design
2. Reference [Code Standards](./code-standards.md) for patterns
3. Check [Project PDR](./project-overview-pdr.md) for requirements
4. Follow error handling in [API Reference](./api-reference.md)

**Key files:** system-architecture.md, code-standards.md

### DevOps / Operations

1. Check [Project PDR - Deployment](./project-overview-pdr.md#deployment)
2. Review [System Architecture - Deployment](./system-architecture.md#deployment-architecture)
3. Reference [README - Architecture](../README.md#architecture)

**Key files:** project-overview-pdr.md, system-architecture.md

### Frontend / Integration Engineer

1. Start with [API Reference](./api-reference.md)
2. Copy code examples (JavaScript, Python, cURL)
3. Refer to troubleshooting section for common issues
4. Review [Project PDR - API Spec](./project-overview-pdr.md#api-specification)

**Key files:** api-reference.md, project-overview-pdr.md

### Product Manager / Stakeholder

1. Read [README](../README.md) for overview
2. Review [Project PDR](./project-overview-pdr.md) for full scope
3. Check [Development Roadmap](./development-roadmap.md) for timeline

**Key files:** README.md, project-overview-pdr.md, development-roadmap.md

---

## Documentation Structure

```
Event Face Detection MVP Documentation
├── README.md                    (150 lines) Quick start + overview
├── docs/
│   ├── index.md                (this file) Navigation hub
│   ├── codebase-summary.md      (255 lines) Architecture overview
│   ├── system-architecture.md   (327 lines) Technical design
│   ├── code-standards.md        (458 lines) Development guide
│   ├── project-overview-pdr.md  (436 lines) Requirements doc
│   ├── api-reference.md         (511 lines) API endpoints
│   └── development-roadmap.md   (281 lines) Project timeline
└── Total: 2,418 lines | 72 KB
```

---

## Key Concepts

### Architecture

**Three-layer design:**
- **Interface Layer:** CLI (Click) + REST API (FastAPI)
- **Business Logic:** FaceService (DeepFace wrapper)
- **Data Layer:** PostgreSQL + DeepFace embeddings

**Flow:** Image → Preprocess → Extract embedding → PostgreSQL ANN search → Return matches

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API | FastAPI | REST endpoints |
| CLI | Click | Command-line interface |
| ML | DeepFace | Face detection & embeddings |
| Database | PostgreSQL | Vector storage & ANN search |
| ORM | psycopg2 | Database adapter |
| Image Proc | Pillow | Image handling |

### Key Features

- Face search by image (returns confidence scores)
- Photo registration/indexing
- Pre-built representation cache
- Path traversal protection
- CORS configuration
- Environment-based configuration

### Constraints

- Single-face images only (MVP)
- Max 10MB file upload
- Cosine distance metric with 0.40 threshold
- Local file storage (not cloud)

---

## Common Tasks

### Set Up Development Environment

```bash
# See README.md - Quick Start section
pip install -r requirements.txt
docker-compose up -d postgres
python main.py register
```

### Add a New CLI Command

1. Open `src/cli/commands.py`
2. Follow patterns in [Code Standards](./code-standards.md#code-patterns)
3. Reference existing commands (register, search, build)
4. Update [API Reference](./api-reference.md) if needed

### Add a New API Endpoint

1. Review [System Architecture](./system-architecture.md#api-httpservermain--py)
2. Follow patterns in [Code Standards](./code-standards.md#api-handler-pattern)
3. Create Pydantic schema in `src/api/schemas.py`
4. Implement in `src/api/main.py`
5. Document in [API Reference](./api-reference.md)
6. Add tests

### Deploy to Production

1. Read [Project PDR - Deployment](./project-overview-pdr.md#deployment)
2. Follow [System Architecture - Deployment](./system-architecture.md#deployment-architecture)
3. Configure environment variables
4. Start PostgreSQL and API server

### Debug an Issue

1. Check [System Architecture - Error Handling](./system-architecture.md#error-handling-architecture)
2. Review logs and error messages
3. Consult [API Reference - Troubleshooting](./api-reference.md#troubleshooting)
4. Review [Code Standards - Logging](./code-standards.md#logging)

### Integrate with Frontend

1. Start with [API Reference](./api-reference.md)
2. Copy code examples
3. Test with provided cURL commands
4. Use troubleshooting section for common issues

---

## Performance Notes

| Operation | Time | Bottleneck |
|-----------|------|-----------|
| Face detection | 1-2s | DeepFace |
| Embedding extraction | 1-3s | DeepFace |
| Database search | <100ms | Network latency |
| Image preprocess | <100ms | Resize operations |
| **Total Search** | **2-5s** | **DeepFace operations** |

**Optimization:** Use `/build` endpoint to pre-compute embeddings.

---

## Security & Best Practices

### Input Validation
- ✓ File type check (image/* only)
- ✓ File size limit (10MB)
- ✓ Path traversal protection (whitelist validation)

### Data Protection
- ✓ Env vars for secrets (no .env in git)
- ✓ CORS configuration per environment
- ✓ Secure logging (no password logging)

### Reliability
- ✓ Graceful error handling
- ✓ Atomic operations (all-or-nothing)
- ✓ Temporary file cleanup

See [Code Standards - Security Guidelines](./code-standards.md#security-guidelines) for details.

---

## Testing

### Run Tests

```bash
pytest -v                    # All tests
pytest --cov=src/           # With coverage
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests
```

### Test Patterns

See [Code Standards - Testing Standards](./code-standards.md#testing-standards) for:
- Test organization
- Test patterns
- Mocking strategies
- Assertion patterns

---

## FAQ

### Q: Where do I start?

**A:** Read [README](../README.md) first, then choose your role above.

### Q: How do I run the API?

**A:** See [README - Quick Start](../README.md#quick-start).

### Q: What's the API format?

**A:** See [API Reference](./api-reference.md) for all endpoints and examples.

### Q: How do I add a feature?

**A:** Follow [Code Standards](./code-standards.md) patterns and [Project PDR](./project-overview-pdr.md) requirements.

### Q: Where's the deployment guide?

**A:** See [Project PDR - Deployment](./project-overview-pdr.md#deployment) or [System Architecture - Deployment](./system-architecture.md#deployment-architecture).

### Q: How do I debug issues?

**A:** Check [API Reference - Troubleshooting](./api-reference.md#troubleshooting) or [System Architecture - Error Handling](./system-architecture.md#error-handling-architecture).

---

## Updates & Maintenance

### When to Update Documentation

- API endpoints change → Update [API Reference](./api-reference.md)
- Architecture changes → Update [System Architecture](./system-architecture.md)
- Code patterns change → Update [Code Standards](./code-standards.md)
- Requirements change → Update [Project PDR](./project-overview-pdr.md)
- Dependencies change → Update [Codebase Summary](./codebase-summary.md)

### Version Control

All documentation is markdown-based, checked into git.
Use standard git workflow for documentation changes.

---

## Related Resources

### Internal

- [CLAUDE.md](../CLAUDE.md) - AI agent instructions
- [AGENTS.md](../AGENTS.md) - Agent roles and workflows
- [.claude/rules/](../.claude/rules/) - Development rules

### External

- [DeepFace Docs](https://github.com/serengp/deepface)
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Click Docs](https://click.palletsprojects.com/)

---

## Document Metadata

| Property | Value |
|----------|-------|
| Created | 2026-01-19 |
| Last Updated | 2026-01-19 |
| Total Pages | 7 |
| Total Lines | 2,418 |
| Total Size | 72 KB |
| Status | Complete |
| Coverage | 100% |

---

## Feedback & Contributions

Questions about documentation? Found an error?

1. Check the relevant doc file
2. Create an issue or PR
3. Follow update guidelines above

---

**Start here:** [README](../README.md) → Choose your role → Find the docs you need!
