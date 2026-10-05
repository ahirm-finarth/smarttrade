from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.core.config import get_settings
from app.db.session import database_connected


class HealthResponse(BaseModel):
    status: str
    database: str
    llm_configured: bool


app = FastAPI(title="FinArth Smart Trade", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    connected = database_connected()
    payload = HealthResponse(
        status="ok" if connected else "unavailable",
        database="connected" if connected else "unavailable",
        llm_configured=get_settings().llm_configured,
    )
    return JSONResponse(status_code=200 if connected else 503, content=payload.model_dump())
