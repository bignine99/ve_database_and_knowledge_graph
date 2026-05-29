FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application source code
COPY ./src /app/src/

# Copy data files (except data/db ignored by .dockerignore)
COPY ./data /app/data/

# Cloud Run uses PORT env var — shell form to expand $PORT
CMD exec gunicorn -w 1 --threads 4 -b 0.0.0.0:$PORT --timeout 120 src.app:app
