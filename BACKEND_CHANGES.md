# Backend Changes for Clear DB Feature

## Files Modified

### 1. `/backend/routers/admin.py` (NEW FILE)

Created a new admin router with clear database functionality.

```python
from fastapi import APIRouter
from services.weaviate_client import db
from services.neo4j_client import graph_db
from config import settings
import weaviate
from neo4j import GraphDatabase

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/clear-db")
async def clear_database():
    """Clear all data from Weaviate and Neo4j databases"""
    # Clears Weaviate schema
    # Clears Neo4j nodes
    # Recreates fresh Weaviate schema
```

**Endpoint Details:**

- **URL**: `POST http://localhost:8054/admin/clear-db`
- **Method**: POST
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Database cleared successfully"
  }
  ```

### 2. `/backend/main.py` (MODIFIED)

Updated to include the new admin router.

**Changes:**

```python
# Added import
from routers import ingest, query, graph, admin

# Added router registration
app.include_router(admin.router)
```

## How It Works

1. **Weaviate Cleanup**:
   - Deletes all schemas (TextChunk, FigureChunk, AudioChunk)
   - Removes all indexed data

2. **Schema Recreation**:
   - Recreates TextChunk class with properties:
     - paper_id, paper_title, authors, year
     - chunk_text, chunk_index, page
   - Recreates FigureChunk class
   - Recreates AudioChunk class

3. **Neo4j Cleanup**:
   - Runs `MATCH (n) DETACH DELETE n` to remove all nodes and relationships
   - Keeps the database structure intact

## Error Handling

If something goes wrong, the endpoint returns:

```json
{
  "status": "error",
  "message": "Error details here",
  "detail": "Failed to clear database: ..."
}
```

## Frontend Integration

The `ClearDBButton.tsx` component calls this endpoint:

```typescript
const res = await fetch("http://localhost:8054/admin/clear-db", {
  method: "POST",
});
```

## Safety Features

✅ **Frontend Level**:

- Confirmation modal with warning
- Clear messaging about consequences
- Cancel option

✅ **Backend Level**:

- Error handling and logging
- Atomic operations
- Schema recreation on success

## Testing the Feature

```bash
# 1. Start the backend
cd backend
python main.py

# 2. Upload some documents
# Use the frontend to ingest PDFs/audio

# 3. Clear the database
# Click the "🗑️ Clear DB" button in the header

# 4. Verify it works
# Search should return no results
# Upload new documents
```

## Notes

- Clearing the database is **irreversible**
- All documents, audio, and graphs will be deleted
- Use with caution in production
- Consider backing up data before clearing
- The operation is logged (check server console)
