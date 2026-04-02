# ReproLab FastAPI Backend

FastAPI wrapper connecting the React frontend to the Python reproducibility scoring engine.

## Quick Start

### Prerequisites
- Python 3.10+
- pip or uv

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run server:**
   ```bash
   python main.py
   ```
   - API runs on http://localhost:8000
   - Docs available at http://localhost:8000/docs

## Architecture

```
api/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
└── __init__.py
```

## API Endpoints

### Health Check
```
GET /health
```
Returns: `{"status": "ok"}`

### List Protocols
```
GET /protocols
```
Returns array of protocol objects:
```json
[
  {
    "id": "proto_1",
    "name": "DNA Extraction",
    "description": "...",
    "materials": ["Taq polymerase (NEB M0273L)"],
    "methods": ["Step 1: ..."],
    "constraints": ["Temperature: 37°C"],
    "reproducibility_score": {
      "overall": 85,
      "metadata_completeness": 90,
      "reagent_traceability": 80,
      "step_granularity": 75
    }
  }
]
```

### Get Protocol
```
GET /protocols/{protocol_id}
```
Returns single protocol object.

### Create Protocol
```
POST /protocols
Content-Type: application/json

{
  "name": "DNA Extraction Protocol",
  "description": "Standard molecular extraction procedure",
  "materials": ["DNA extraction kit (Qiagen 69504)"],
  "methods": ["Add sample to lysis buffer", "Incubate at 95°C for 10 min"],
  "constraints": ["Store at -20°C"]
}
```
Returns: Created protocol with ID and score.

### Update Protocol
```
PUT /protocols/{protocol_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "description": "...",
  ...
}
```
Returns: Updated protocol with recalculated score.

### Score Protocol (Without Saving)
```
POST /protocols/score
Content-Type: application/json

{
  "name": "Protocol Name",
  "description": "Description",
  "materials": ["..."],
  "methods": ["..."],
  "constraints": ["..."]
}
```
Returns:
```json
{
  "overall": 75,
  "metadata_completeness": 80,
  "reagent_traceability": 70,
  "step_granularity": 65
}
```

### Delete Protocol
```
DELETE /protocols/{protocol_id}
```
Returns: `{"message": "Protocol deleted"}`

## Scoring Algorithm

Reproducibility score combines three components:

| Component | Weight | Calculation |
|-----------|--------|-------------|
| Metadata Completeness | 45% | Name + description + constraints present |
| Reagent Traceability | 35% | Materials with catalog numbers present |
| Step Granularity | 20% | Number and detail of method steps |

**Final Score = 45% × metadata + 35% × traceability + 20% × granularity**

Range: 0-100

## Integration with Python Backend

The API imports and uses the ReproLab Python package:

```python
from reprolab import ReproLabPipeline
from reprolab.scoring import ReproducibilityScorer

scorer = ReproducibilityScorer()
score = scorer.score(protocol_dict, log_frame)
```

Scoring results are wrapped in HTTP responses with proper error handling.

## CORS Configuration

Allowed origins (configured in `main.py`):
- `http://localhost:5173` (React dev server)
- `http://localhost:3000` (Alternative React dev port)

## Error Handling

```json
{
  "detail": "Protocol not found"
}
```

HTTP Status Codes:
- `200` - Success
- `404` - Not found
- `422` - Validation error
- `500` - Server error

## Development

### Interactive Docs
Run server and navigate to: http://localhost:8000/docs

Swagger UI provides interactive API testing.

### Logging
Enable debug logging in `main.py`:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Production Deployment

1. Use production ASGI server (Gunicorn):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker api.main:app
   ```

2. Configure environment variables
3. Set CORS origins to production domains
4. Replace in-memory storage with Supabase

## Data Storage

Currently uses in-memory dictionary (`protocols_store`). 

**Future: Migrate to Supabase PostgreSQL**
- User authentication via Supabase Auth
- Protocol data in `protocols` table
- Multi-tenant isolation
- Audit trail logging

## Testing

```bash
# Interactive API docs
curl http://localhost:8000/health

# Score a protocol
curl -X POST http://localhost:8000/protocols/score \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "materials": ["Item 1"], "methods": ["Step 1"], "constraints": []}'
```
