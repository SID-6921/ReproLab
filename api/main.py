from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import sys
import os

# Add parent directory to path to import reprolab
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from reprolab import ReproLabPipeline, PipelineResult
from reprolab.scoring import ReproducibilityScorer

app = FastAPI(title="ReproLab API", version="0.1.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline and scorer
pipeline = ReproLabPipeline()
scorer = ReproducibilityScorer()

# Pydantic models
class ProtocolInput(BaseModel):
    name: str
    description: Optional[str] = ""
    materials: List[str] = []
    methods: List[str] = []
    constraints: List[str] = []

class ProtocolResponse(ProtocolInput):
    id: str
    reproducibility_score: Optional[dict] = None

class ScoreRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    materials: List[str] = []
    methods: List[str] = []
    constraints: List[str] = []

class ScoreResponse(BaseModel):
    overall: int
    metadata_completeness: int
    reagent_traceability: int
    step_granularity: int

# In-memory storage (replace with Supabase in production)
protocols_store: dict = {}
protocol_counter: int = 0

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

@app.get("/protocols")
async def list_protocols():
    """List all protocols for the current user"""
    return list(protocols_store.values())

@app.get("/protocols/{protocol_id}")
async def get_protocol(protocol_id: str):
    """Get a specific protocol"""
    if protocol_id not in protocols_store:
        raise HTTPException(status_code=404, detail="Protocol not found")
    return protocols_store[protocol_id]

@app.post("/protocols")
async def create_protocol(protocol: ProtocolInput):
    """Create a new protocol"""
    global protocol_counter
    protocol_counter += 1
    protocol_id = f"proto_{protocol_counter}"
    
    # Create protocol data structure
    protocol_data = {
        "id": protocol_id,
        **protocol.dict(),
        "reproducibility_score": None
    }
    
    # Score the protocol
    scoring_data = {
        "name": protocol.name,
        "materials": protocol.materials,
        "methods": protocol.methods,
        "constraints": protocol.constraints,
        "description": protocol.description,
    }
    try:
        score = scorer.score(scoring_data, {})
        protocol_data["reproducibility_score"] = score.model_dump() if hasattr(score, 'model_dump') else score.__dict__
    except Exception as e:
        print(f"Scoring error: {e}")
        protocol_data["reproducibility_score"] = {
            "overall": 0,
            "metadata_completeness": 0,
            "reagent_traceability": 0,
            "step_granularity": 0,
        }
    
    protocols_store[protocol_id] = protocol_data
    return protocol_data

@app.put("/protocols/{protocol_id}")
async def update_protocol(protocol_id: str, protocol: ProtocolInput):
    """Update an existing protocol"""
    if protocol_id not in protocols_store:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    # Update protocol data
    protocol_data = {
        "id": protocol_id,
        **protocol.dict(),
        "reproducibility_score": None
    }
    
    # Re-score the protocol
    scoring_data = {
        "name": protocol.name,
        "materials": protocol.materials,
        "methods": protocol.methods,
        "constraints": protocol.constraints,
        "description": protocol.description,
    }
    try:
        score = scorer.score(scoring_data, {})
        protocol_data["reproducibility_score"] = score.model_dump() if hasattr(score, 'model_dump') else score.__dict__
    except Exception as e:
        print(f"Scoring error: {e}")
        protocol_data["reproducibility_score"] = {
            "overall": 0,
            "metadata_completeness": 0,
            "reagent_traceability": 0,
            "step_granularity": 0,
        }
    
    protocols_store[protocol_id] = protocol_data
    return protocol_data

@app.post("/protocols/score")
async def score_protocol(protocol: ScoreRequest):
    """Score a protocol without saving it"""
    scoring_data = {
        "name": protocol.name,
        "materials": protocol.materials,
        "methods": protocol.methods,
        "constraints": protocol.constraints,
        "description": protocol.description,
    }
    
    try:
        score = scorer.score(scoring_data, {})
        # Convert score object to dict
        if hasattr(score, 'model_dump'):
            return score.model_dump()
        elif hasattr(score, '__dict__'):
            return score.__dict__
        else:
            return {
                "overall": score.overall,
                "metadata_completeness": score.metadata_completeness,
                "reagent_traceability": score.reagent_traceability,
                "step_granularity": score.step_granularity,
            }
    except Exception as e:
        print(f"Scoring error: {e}")
        return {
            "overall": 0,
            "metadata_completeness": 0,
            "reagent_traceability": 0,
            "step_granularity": 0,
        }

@app.delete("/protocols/{protocol_id}")
async def delete_protocol(protocol_id: str):
    """Delete a protocol"""
    if protocol_id not in protocols_store:
        raise HTTPException(status_code=404, detail="Protocol not found")
    
    del protocols_store[protocol_id]
    return {"message": "Protocol deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
