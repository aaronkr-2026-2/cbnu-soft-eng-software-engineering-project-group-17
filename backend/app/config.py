"""Application settings, read once from environment variables.

Keeping every setting in one place makes it easy to see what can be
configured (see also `.env.example` in the repository root).
"""
import os
from pathlib import Path

# --- Database -------------------------------------------------------------
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "sleepinsight")
# USE_MOCK_DB=1 runs the app against an in-memory fake MongoDB (mongomock).
# Handy for a quick demo or for tests; data is lost when the process stops.
USE_MOCK_DB = os.environ.get("USE_MOCK_DB", "0") == "1"

# --- Upload limits --------------------------------------------------------
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024
MIN_EPOCHS = 60      # at least one hour of data (1 epoch = 1 minute)
MAX_EPOCHS = 2000    # about 33 hours; protects against huge files

# --- Sleep-stage model ----------------------------------------------------
MODEL_DIR = Path(os.environ.get("MODEL_DIR", Path(__file__).resolve().parent / "model_store"))
TRAIN_NIGHTS = int(os.environ.get("TRAIN_NIGHTS", "60"))  # synthetic nights used for training

# --- Frontend -------------------------------------------------------------
# The backend serves the static web interface from ../../frontend.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
