# Single image: FastAPI backend + the static web interface it serves.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so Docker can reuse this layer when only the code changes.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

WORKDIR /app/backend

# Train the sleep-stage model at build time (takes a few seconds), so the first
# request after startup is fast and the container does not need to write a model.
RUN python -m app.services.training

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
