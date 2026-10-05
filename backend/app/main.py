from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.cases import router
from app.api.v1.documents import router as document_router
from app.api.v1.examinations import router as examination_router
from app.api.v1.risk import router as risk_router
from app.core.config import get_settings
from app.db.session import database_connected
from app.integrations.storage.local import InvalidDocument
from app.services.cases import CaseNotFound
from app.services.documents import DocumentConflict, DocumentNotFound
from app.services.examination_engine import ExaminationNotConfigured, ExaminationNotFound
from app.services.risk_orchestration import RiskRunNotFound


class HealthResponse(BaseModel):
    status: str
    database: str
    llm_configured: bool


app = FastAPI(title="FinArth Smart Trade", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
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


app.include_router(router)
app.include_router(document_router)
app.include_router(examination_router)
app.include_router(risk_router)


@app.exception_handler(RiskRunNotFound)
async def risk_run_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Risk run not found"})


@app.exception_handler(ExaminationNotFound)
async def examination_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Documentary examination not found"})


@app.exception_handler(ExaminationNotConfigured)
async def examination_not_configured(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(CaseNotFound)
async def case_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Trade case not found"})


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable"})


@app.exception_handler(DocumentNotFound)
async def document_not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Source document or version not found"})


@app.exception_handler(InvalidDocument)
async def invalid_document(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(DocumentConflict)
async def document_conflict(request, exc):
    return JSONResponse(status_code=409, content={"detail": str(exc)})
