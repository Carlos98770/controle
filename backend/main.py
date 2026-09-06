import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import numpy as np

try:
    from .calculations import analyze
except ImportError:
    # Mantém o comando local `uvicorn main:app --app-dir backend` funcionando.
    from calculations import analyze

app = FastAPI(title="LGR API", version="1.0.0")
configured_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]
allowed_origins = ["http://localhost:5173", "http://localhost:3000", *configured_origins]
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(allowed_origins)),
    # Permite previews da Vercel; domínios próprios entram em FRONTEND_ORIGINS.
    allow_origin_regex=r"^https://[a-z0-9-]+\.vercel\.app$",
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    nG: str = "1 2"
    dG: str = "1 4 0"
    nH: str = "1"
    dH: str = "1 1"
    pointReal: float = 0
    pointImag: float = 0


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/analyze")
def calculate(request: AnalysisRequest):
    try:
        return analyze(request.model_dump())
    except (ValueError, np.linalg.LinAlgError) as error:
        raise HTTPException(status_code=400, detail=str(error))
