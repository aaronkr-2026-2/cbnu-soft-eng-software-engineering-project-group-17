"""FastAPI application: JSON API under /api and the static web interface at /."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import ConnectionFailure

from . import config
from .db import ensure_indexes, get_client
from .routers import analytics, context, demo, nights
from .services import staging

log = logging.getLogger("sheepcounter")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup work: create indexes and make sure the sleep-stage model exists."""
    try:
        ensure_indexes(get_client()[config.DB_NAME])
    except ConnectionFailure:
        log.warning("MongoDB is not reachable at startup; API calls will return 503 until it is.")
    staging.get_model_bundle()  # trains once (a few seconds) if no saved model is found
    yield


app = FastAPI(
    title="Sheepcounter",
    description="Sleep analysis prototype: import or generate nights, detect sleep stages, get insights and a smart alarm. "
    "Not a medical device.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(ConnectionFailure)
async def database_unavailable(request: Request, exc: ConnectionFailure):
    return JSONResponse(status_code=503, content={"detail": "Database is not available. Is MongoDB running?"})


@app.get("/api/health", tags=["meta"])
def health():
    return {"status": "ok"}


app.include_router(nights.router)
app.include_router(context.router)
app.include_router(analytics.router)
app.include_router(demo.router)

# Must come last: it serves everything that is not an /api route.
app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
