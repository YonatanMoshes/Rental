# FastAPI Backend Docker Image
# 
# Multi-stage build optimization:
#   - Base: Python 3.12 slim (small footprint)
#   - Dependencies installed with pip
#   - Application code copied in
#   - Exposes port 8000 for Uvicorn server
# 
# Build: docker build -f Dockerfile -t rental-backend .
# Run:   docker run -p 8000:8000 rental-backend

FROM python:3.12-slim

WORKDIR /app

# Copy only essential files (requirements, README, backend code)
COPY pyproject.toml README.md ./
COPY backend ./backend

# Install dependencies in one layer (no cache bloat)
RUN pip install --no-cache-dir .

# Expose Uvicorn port
EXPOSE 8000

# Start FastAPI server with Uvicorn
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
