# ReproLab Full-Stack Deployment Guide

This guide walks through deploying the complete ReproLab system: Python backend, FastAPI API wrapper, and React frontend.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend (Vite)                    │
│               http://localhost:5173 (dev)                   │
│                                                              │
│  • Supabase Authentication                                  │
│  • Protocol Editor with Live Scoring                        │
│  • Dashboard and Protocol Management                        │
└─────────────────────┬───────────────────────────────────────┘
                      │ HTTP Requests
                      │ (/api/*)
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (api/main.py)                  │
│               http://localhost:8000                         │
│                                                              │
│  • CORS enabled for frontend dev                            │
│  • Protocol CRUD operations                                 │
│  • Real-time scoring via ReproLab Python engine             │
└─────────────────────┬───────────────────────────────────────┘
                      │ Imports
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│           ReproLab Python Engine (src/reprolab/)            │
│                                                              │
│  • ReproducibilityScorer class                              │
│  • Scoring algorithm (45/35/20 weights)                     │
│  • Protocol validation & preprocessing                      │
│  • Lineage tracking & constraint engine                     │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Global Requirements
- Git
- Node.js 18+
- Python 3.10+

### Services
- **Supabase** (free tier): https://supabase.com
  - For authentication and optional data storage

### Local Development Tools
- VS Code (recommended)
- Postman or cURL (for API testing)

---

## Phase 1: Backend Setup (Python)

### 1.1 Install Python Backend

The Python backend should already be installed from the main ReproLab setup:

```bash
# From ReproLab root
python -m pip install -e .[dev]
```

Verify installation:
```bash
python -c "from reprolab.scoring import ReproducibilityScorer; print('✓ ReproLab installed')"
```

### 1.2 Run Tests

```bash
python -m pytest
```

Expected output: `7 passed` (scoring + existing tests)

---

## Phase 2: API Server Setup (FastAPI)

### 2.1 Install Dependencies

```bash
cd api
pip install -r requirements.txt
```

### 2.2 Start API Server

```bash
python main.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### 2.3 Verify API

In another terminal:
```bash
curl http://localhost:8000/health
# Returns: {"status":"ok"}
```

Interactive docs: http://localhost:8000/docs

### 2.4 Test Scoring Endpoint

```bash
curl -X POST http://localhost:8000/protocols/score \
  -H "Content-Type: application/json" \
  -d '{
    "name": "DNA Extraction",
    "materials": ["Taq polymerase (NEB M0273L)"],
    "methods": ["Add sample to lysis buffer", "Incubate at 95°C for 10 min"],
    "constraints": ["Temperature: 37°C ± 2°C"]
  }'
```

Expected response:
```json
{
  "overall": 67,
  "metadata_completeness": 70,
  "reagent_traceability": 65,
  "step_granularity": 60
}
```

---

## Phase 3: Frontend Setup (React)

### 3.1 Install Dependencies

```bash
cd frontend
npm install
```

### 3.2 Configure Supabase

1. **Create Supabase project** at https://supabase.com
2. **Get credentials:**
   - Project URL: https://YOUR-PROJECT.supabase.co
   - Anon Key: In Settings → API

3. **Create `.env.local`:**
   ```bash
   cp .env.example .env.local
   ```

4. **Edit `.env.local`:**
   ```env
   VITE_SUPABASE_URL=https://YOUR-PROJECT.supabase.co
   VITE_SUPABASE_ANON_KEY=your-anon-key
   VITE_API_URL=http://localhost:8000
   ```

### 3.3 Enable Authentication in Supabase

1. Go to Supabase dashboard → Authentication
2. Click "Users" → "Add User"
3. Create test user (email + password)

### 3.4 Start Frontend

```bash
npm run dev
```

Expected output:
```
  VITE v5.0.0  ready in 234 ms

  ➜  Local:   http://localhost:5173/
  ➜  Press q to return to normal..
```

---

## Phase 4: End-to-End Testing

### 4.1 Login

1. Navigate to http://localhost:5173
2. Click "Sign Up" or "Sign In"
3. Use test credentials from Supabase user

### 4.2 Create Protocol

1. Click "New Protocol" button
2. Fill in:
   - **Protocol Name**: "DNA Extraction"
   - **Description**: "Standard molecular extraction"
   - **Materials**: Add "Taq polymerase (NEB M0273L)"
   - **Methods**: Add "Incubate at 95°C for 10 min"
   - **Constraints**: Add "Temperature: 37°C ± 2°C"
3. **Observe:** Reproducibility score updates in real-time (right panel)
4. Click "Save Protocol"

### 4.3 Verify Score

Score should show components:
- Metadata Completeness: ~70
- Reagent Traceability: ~65
- Step Granularity: ~60
- Overall: ~67

### 4.4 API Call Verification

```bash
curl http://localhost:8000/protocols
# Should return created protocol in JSON array
```

---

## Production Deployment

### Frontend (Vercel/Netlify)

1. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "feat: add react frontend and fastapi api"
   git push origin main
   ```

2. **Deploy with Vercel:**
   - Go to https://vercel.com
   - Connect GitHub repo
   - Set environment variables:
     ```
     VITE_SUPABASE_URL=<production-url>
     VITE_SUPABASE_ANON_KEY=<production-key>
     VITE_API_URL=https://api.reprolab.io
     ```
   - Click "Deploy"

### API (AWS/Heroku/Railway)

**Option 1: Heroku**

```bash
cd api
heroku login
heroku create reprolab-api
heroku config:set REPROLAB_ENV=production
git push heroku main
```

**Option 2: Railway**

- Connect GitHub repo at https://railway.app
- Select `api/main.py` as root
- Set environment variables
- Deploy

**Option 3: AWS Lambda (with Mangum)**

```bash
pip install mangum
```

Create `api/lambda_handler.py`:
```python
from mangum import Mangum
from api.main import app

handler = Mangum(app)
```

---

## Multi-Tenant Setup (Advanced)

### Enable Supabase for Data Storage

1. **Create `protocols` table in Supabase:**

   ```sql
   CREATE TABLE protocols (
     id UUID PRIMARY KEY REFERENCES auth.users,
     user_id UUID NOT NULL REFERENCES auth.users(id),
     name TEXT NOT NULL,
     description TEXT,
     materials JSONB[],
     methods JSONB[],
     constraints JSONB[],
     reproducibility_score JSONB,
     created_at TIMESTAMP DEFAULT NOW(),
     updated_at TIMESTAMP DEFAULT NOW()
   );
   ```

2. **Update `api/main.py` to use Supabase:**

   ```python
   from supabase import create_client
   
   supabase = create_client(
     os.environ["SUPABASE_URL"],
     os.environ["SUPABASE_KEY"]
   )
   ```

3. **Modify protocol endpoints** to read/write to `protocols` table

---

## Troubleshooting

### Frontend won't connect to API

**Error:** `Failed to fetch from /api/protocols`

**Fix:**
1. Verify API running: `curl http://localhost:8000/health`
2. Check CORS: API should log `CORS(*): * allows usage`
3. Verify proxy in `vite.config.js` points to `:8000`

### Supabase auth not working

**Error:** `Missing Supabase environment variables`

**Fix:**
1. `cp .env.example .env.local`
2. Check `.env.local` has correct URL and key
3. Reload browser (Ctrl+Shift+R)

### Scoring returns 0

**Error:** Score always shows `0/0/0/0`

**Fix:**
1. Check API logs for Python errors
2. Verify ReproLab installed: `pip list | grep reprolab`
3. Manually test scorer:
   ```python
   from reprolab.scoring import ReproducibilityScorer
   scorer = ReproducibilityScorer()
   score = scorer.score({"name": "Test", "materials": []}, {})
   print(score)
   ```

---

## Architecture Decision Record

### Why Monorepo?
- Tight integration between React UI and Python engine
- Single version control for full product
- Shared documentation and CI/CD

### Why REST API?
- Standard for web services
- Easy debugging (browser DevTools)
- Simple to scale horizontally
- WebSocket can be added for real-time later

### Why Supabase?
- Drop-in PostgreSQL with auth
- Real-time subscriptions
- Multi-tenant support built-in
- Free tier sufficient for MVP

### Why Zustand for state?
- Lightweight (1.2 KB)
- No boilerplate
- Perfect for auth + protocol state
- Easy to migrate to Redux later

---

## Next Steps

1. **Add Supabase data storage** (optional for MVP)
2. **Implement real-time updates** with WebSocket
3. **Add payments** with Stripe
4. **Build mobile app** with React Native
5. **Add audit logging** for compliance

---

## Support

- Backend docs: [../README.md](../README.md)
- API docs: [./api/README.md](./api/README.md)
- Frontend docs: [./frontend/README.md](./frontend/README.md)
- Issues: https://github.com/SID-6921/ReproLab/issues
