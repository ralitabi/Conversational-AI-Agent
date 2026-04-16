# ── Stage 1: Build React frontend ────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --silent

COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python backend ───────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install Python deps first (cached layer)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Drop the React dev source; only the compiled build is needed
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Railway injects $PORT at runtime (default 8080)
ENV PORT=8080
EXPOSE 8080

CMD uvicorn backend.api:app --host 0.0.0.0 --port ${PORT} --workers 2
