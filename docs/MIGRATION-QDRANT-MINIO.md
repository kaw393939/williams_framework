# Architecture Changes - Qdrant + MinIO Migration

**Date**: October 9, 2025  
**Status**: Phase 2 - Data Layer Implementation

## Summary of Changes

We've upgraded from ChromaDB + local filesystem to **Qdrant + MinIO** for better production readiness, scalability, and industry-standard compatibility.

## What Changed

### Vector Database: ChromaDB → Qdrant

**Why Qdrant?**
- ✅ **Production-ready**: Battle-tested in real-world deployments
- ✅ **Docker-native**: Official Docker images, easy orchestration
- ✅ **Better performance**: Optimized for high-throughput scenarios
- ✅ **RESTful API**: Easy debugging and monitoring
- ✅ **Advanced filtering**: Better metadata queries
- ✅ **Horizontal scaling**: Can scale across multiple nodes

**Migration Details**:
- Replace `chromadb` → `qdrant-client` in dependencies
- Docker service on ports 6333 (REST), 6334 (gRPC)
- Collection-based organization (vs ChromaDB's client/collection model)
- COSINE distance metric for semantic similarity
- 384-dimensional vectors (sentence-transformers standard)

**Config Changes**:
```python
# OLD (ChromaDB)
chroma_persist_dir: str = "./data/chroma"
chroma_collection_name: str = "librarian_collection"

# NEW (Qdrant)
qdrant_host: str = "localhost"
qdrant_port: int = 6333
qdrant_grpc_port: int = 6334
qdrant_collection_name: str = "librarian_embeddings"
```

### File Storage: Local Filesystem → MinIO

**Why MinIO?**
- ✅ **S3-compatible**: Industry standard API (AWS S3, Cloudflare R2, Backblaze B2)
- ✅ **Scalable**: No local disk limits, horizontal scaling
- ✅ **Better metadata**: S3 object metadata and tags
- ✅ **Production-ready**: Used by Netflix, Uber, etc.
- ✅ **Docker-native**: Official images, easy setup
- ✅ **Versioning**: Built-in file version tracking
- ✅ **Access control**: Bucket policies, IAM-like permissions
- ✅ **Future-proof**: Easy migration to cloud providers

**Storage Architecture**:
```
MinIO Buckets:
├── tier-a/          # Quality 9.0-10.0 (premium content)
├── tier-b/          # Quality 7.0-8.9 (good content)
├── tier-c/          # Quality 5.0-6.9 (acceptable content)
└── tier-d/          # Quality 0.0-4.9 (low-priority content)

Each object:
- Key: content_id or URL hash
- Content: Markdown file
- Metadata: url, title, quality_score, source_type, tags, created_at
- Tags: topic, author, year, etc.
```

**Config Changes**:
```python
# OLD (Local Filesystem)
library_root: str = "./library"

# NEW (MinIO)
minio_endpoint: str = "localhost:9000"
minio_access_key: str = "minioadmin"
minio_secret_key: str = "minioadmin"
minio_secure: bool = False  # True for production with TLS
```

## Implementation Status

### ✅ Completed

1. **Phase 1: Foundation Layer** (107 tests, 98.05% coverage)
   - All domain models
   - Configuration system
   - Custom exceptions

2. **Phase 2.1: Qdrant Repository** (17 tests, 85% coverage)
   - Add, query, delete, update operations
   - Metadata filtering
   - Batch operations
   - Real Qdrant integration tests

3. **Documentation Updates**
   - Updated `architecture.md` with Qdrant/MinIO
   - Updated `IMPLEMENTATION-SUMMARY.md` tech stack
   - Created this migration changelog

### 🚧 In Progress

4. **Phase 2.2: MinIO Object Storage Repository**
   - Add MinIO service to docker-compose.yml
   - Implement S3Repository with minio client
   - Bucket management (create tier buckets)
   - Upload/download/delete operations
   - Metadata and tagging
   - Integration tests with real MinIO

### ⏳ Upcoming

5. **Phase 2.3: PostgreSQL Metadata Repository**
6. **Phase 2.4: Redis Cache Layer**
7. **Phase 3+**: Application, Intelligence, ETL, Presentation layers

## Docker Compose Services

### Current Stack

```yaml
services:
  postgres:      # Port 5432 - Metadata storage
  redis:         # Port 6379 - Cache layer
  qdrant:        # Ports 6333, 6334 - Vector database
  minio:         # Port 9000 (API), 9001 (Console) - Object storage [ADDING]
```

## Breaking Changes

### For Developers

1. **Update .env file**:
   ```bash
   # Remove
   CHROMA_PERSIST_DIR=./data/chroma
   CHROMA_COLLECTION_NAME=librarian_collection
   
   # Add
   QDRANT_HOST=localhost
   QDRANT_PORT=6333
   QDRANT_GRPC_PORT=6334
   QDRANT_COLLECTION_NAME=librarian_embeddings
   
   MINIO_ENDPOINT=localhost:9000
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin
   MINIO_SECURE=false
   ```

2. **Update imports**:
   ```python
   # OLD
   from app.repositories.chroma_repository import ChromaRepository
   
   # NEW
   from app.repositories.qdrant_repository import QdrantRepository
   from app.repositories.minio_repository import MinIORepository
   ```

3. **Repository interface changes**:
   ```python
   # OLD (ChromaDB)
   chroma_repo.add_document(doc)
   chroma_repo.search(query, k=5)
   
   # NEW (Qdrant)
   qdrant_repo.add(content_id, vector, metadata)
   qdrant_repo.query(query_vector, limit=5)
   
   # OLD (Filesystem)
   file_repo.save_file(content, path)
   
   # NEW (MinIO)
   minio_repo.upload_file(bucket, key, content, metadata)
   ```

## Testing Impact

### Integration Tests

- **Qdrant tests**: 17 tests using REAL Qdrant instance (NO MOCKS)
- **MinIO tests**: Will add ~15 tests using REAL MinIO instance (NO MOCKS)
- **All tests run against Docker services**: Ensures production parity

### Test Execution

```bash
# Start all services
sudo docker compose up -d

# Run integration tests
poetry run pytest tests/integration/ -v

# Check service health
curl http://localhost:6333/health  # Qdrant
curl http://localhost:9000/minio/health/live  # MinIO
```

## Migration Path (Future)

### From Development to Production

**Development** (current):
- Qdrant: Local Docker container
- MinIO: Local Docker container
- Data: Stored locally

**Production** (future, easy migration):
- Qdrant: Qdrant Cloud or self-hosted cluster
- MinIO: AWS S3 / Cloudflare R2 / Backblaze B2
- Config change only - code stays the same!

```python
# Production config (future)
qdrant_host: str = "qdrant-cluster.production.com"
minio_endpoint: str = "s3.amazonaws.com"  # or r2.cloudflar econfig.com
minio_region: str = "us-east-1"
minio_secure: bool = True
```

## Performance Improvements

### Qdrant vs ChromaDB

- **Query speed**: ~2-5x faster for large collections (>100k vectors)
- **Indexing**: HNSW algorithm, optimized for billions of vectors
- **Filtering**: Native support for complex metadata queries
- **Memory**: More efficient memory usage

### MinIO vs Local Filesystem

- **Scalability**: Unlimited storage vs disk constraints
- **Redundancy**: Built-in replication and erasure coding
- **Access**: HTTP API vs file I/O (easier for distributed systems)
- **Metadata**: Rich object metadata vs limited file attributes

## Documentation Updates Needed

The following files still reference ChromaDB and need updates:

1. ~~`docs/architecture.md`~~ ✅ UPDATED
2. ~~`docs/IMPLEMENTATION-SUMMARY.md`~~ ✅ UPDATED
3. `docs/deployment.md` - Update docker-compose examples
4. `docs/tdd-implementation-plan.md` - Update Phase 2 tests
5. `docs/testing-guide.md` - Update integration test examples
6. `README.md` - Update tech stack section

## Questions & Answers

**Q: Why not keep ChromaDB for simpler local development?**  
A: Qdrant is just as easy locally (single Docker container) and provides better production parity.

**Q: Can I still run this without Docker?**  
A: Yes, but you'll need to install and run Qdrant and MinIO separately. Docker is highly recommended.

**Q: What about existing ChromaDB data?**  
A: We haven't built the system yet, so no migration needed. This is the right time to make this change!

**Q: Is MinIO overkill for local development?**  
A: No! It's lightweight, and using S3-compatible storage from day one means production deployment is trivial.

**Q: What's the learning curve?**  
A: Minimal. Qdrant client is similar to ChromaDB. MinIO uses standard S3 API (boto3/minio-py).

## Benefits Summary

✅ **Production-ready from day one**  
✅ **Industry-standard technologies**  
✅ **Easy cloud migration path**  
✅ **Better performance and scalability**  
✅ **Richer metadata capabilities**  
✅ **Consistent Docker-based development**  
✅ **S3 compatibility = vendor flexibility**  

## Next Steps

1. ✅ Update documentation (this file + architecture docs)
2. 🚧 Add MinIO to docker-compose.yml
3. 🚧 Implement MinIORepository with integration tests
4. ⏳ Update remaining docs (deployment, testing guide)
5. ⏳ Continue with Phase 2.3 (PostgreSQL) and 2.4 (Redis)

---

**Note**: All changes maintain backward compatibility at the service layer. Application code using repositories will not need changes due to clean architecture principles.
