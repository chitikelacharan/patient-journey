import os
import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, PlainTextResponse
from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models.orm_models import Patient, ClinicalEvent
from backend.app.data.synthetic_generator import seed_synthetic_database

from backend.app.api.routes_ingest import router as ingest_router
from backend.app.api.routes_journeys import router as journeys_router
from backend.app.api.routes_bottlenecks import router as bottlenecks_router
from backend.app.api.routes_ai_correlation import router as ai_router
from backend.app.api.routes_adversarial import router as adversarial_router
from backend.app.api.routes_audit import router as audit_router

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

# Auto-seed database if empty
def initialize_dataset():
    db = SessionLocal()
    try:
        count = db.query(Patient).count()
        if count == 0:
            print("[INFO] Database empty. Seeding realistic patient journeys and adversarial benchmarks...")
            seed_synthetic_database(db, num_patients=120)
            print("[SUCCESS] Database seeded successfully.")
    except Exception as e:
        print(f"[WARN] Database initialization error: {e}")
    finally:
        db.close()

initialize_dataset()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Multi-component healthcare operations intelligence system for journey reconstruction, adversarial resilience, and systemic bottleneck mitigation.",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metric counters for Prometheus
REQUEST_COUNT = 0
ERROR_COUNT = 0
START_TIME = time.time()

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    global REQUEST_COUNT, ERROR_COUNT
    REQUEST_COUNT += 1
    start_ts = time.time()
    try:
        response = await call_next(request)
        if response.status_code >= 500:
            ERROR_COUNT += 1
        return response
    except Exception as exc:
        ERROR_COUNT += 1
        raise exc

# Include API Routers
app.include_router(ingest_router, prefix=settings.API_V1_STR)
app.include_router(journeys_router, prefix=settings.API_V1_STR)
app.include_router(bottlenecks_router, prefix=settings.API_V1_STR)
app.include_router(ai_router, prefix=settings.API_V1_STR)
app.include_router(adversarial_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)

# Level 4 Enterprise Monitoring & Health Endpoints
@app.get("/health", tags=["Observability"])
def health_check():
    """Kubernetes liveness and readiness probe."""
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "hipaa_audit_mode": "ACTIVE_SHA256"
    }

@app.get("/metrics", response_class=PlainTextResponse, tags=["Observability"])
def prometheus_metrics():
    """Prometheus-compatible operational telemetry scrape endpoint."""
    uptime = time.time() - START_TIME
    metrics_text = (
        f"# HELP medpulse_uptime_seconds Total runtime in seconds\n"
        f"# TYPE medpulse_uptime_seconds gauge\n"
        f"medpulse_uptime_seconds {uptime:.2f}\n\n"
        f"# HELP medpulse_http_requests_total Total HTTP requests handled\n"
        f"# TYPE medpulse_http_requests_total counter\n"
        f"medpulse_http_requests_total {REQUEST_COUNT}\n\n"
        f"# HELP medpulse_http_errors_total Total 5xx server errors\n"
        f"# TYPE medpulse_http_errors_total counter\n"
        f"medpulse_http_errors_total {ERROR_COUNT}\n"
    )
    return metrics_text

# Mount Frontend Static Files if directory exists
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend_index():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html not found"}
