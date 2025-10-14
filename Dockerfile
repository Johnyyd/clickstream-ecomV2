# syntax=docker/dockerfile:1
FROM python:3.11-slim AS base

# Install system dependencies (Java for PySpark, and runtime basics)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       openjdk-17-jre-headless \
       ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PATH="$JAVA_HOME/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

FROM base AS deps
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
RUN useradd -ms /bin/bash appuser
USER appuser
COPY --from=deps /usr/local /usr/local
COPY . /app

# Environment defaults (can be overridden by compose)
ENV HOST=0.0.0.0 \
    PORT=8000 \
    MONGO_URI=mongodb://mongo:27017 \
    MONGO_DB=clickstream \
    USE_SPARK=false

EXPOSE 8000

# Run the FastAPI server with Uvicorn
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
