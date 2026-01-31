# Production Dockerfile for FastAPI Application

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for ML and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    ffmpeg \
    libsndfile1 \
    libgomp1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Expose port (Railway will set $PORT env var)
ENV PORT=8000

# Run application via Python script that reads PORT from environment
CMD ["python", "run.py"]
