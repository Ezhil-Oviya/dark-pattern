import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config.database import check_mongo_connection, get_mongo_diagnostics
from app.routes.website_routes import router as website_router
from app.routes.automation_routes import router as automation_router
from app.routes.data_quality_routes import router as data_quality_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup and shutdown checks.
    """
    # Startup: Check MongoDB connectivity
    logger.info("Starting Dark Pattern Compliance Framework API...")
    conn_result = check_mongo_connection()
    is_connected, msg = conn_result
    diagnostics = get_mongo_diagnostics(connection_check=conn_result)

    if is_connected:
        logger.info(f"MongoDB Connectivity: ONLINE | Website DB: '{diagnostics.get('website_database')}' | Evidence DB: '{diagnostics.get('evidence_database')}'")
    else:
        logger.warning(
            f"MongoDB Connectivity: OFFLINE | Status: {msg} | Server: {diagnostics.get('server')}\n"
            "  * If using MongoDB Atlas, ensure your IP address is added to Atlas Network Access (Security -> Network Access -> Add IP -> 0.0.0.0/0)."
        )


    yield

    # Shutdown
    logger.info("Shutting down Dark Pattern Compliance Framework API...")


app = FastAPI(
    title="Dark Pattern Compliance Framework",
    lifespan=lifespan
)

# Allow React frontend CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    website_router,
    prefix="/api/v1",
    tags=["Website Configuration"]
)

app.include_router(
    automation_router,
    prefix="/api/v1",
    tags=["Automation"]
)

app.include_router(
    data_quality_router,
    prefix="/api/v1",
    tags=["Data Quality Assessment"]
)

# Ensure artifacts directory exists for static file serving
artifacts_dir = Path("artifacts")
artifacts_dir.mkdir(parents=True, exist_ok=True)

app.mount(
    "/artifacts",
    StaticFiles(directory=str(artifacts_dir)),
    name="artifacts"
)


@app.get("/")
def home():
    return {
        "message": "Dark Pattern Compliance Auditing Framework API is running"
    }