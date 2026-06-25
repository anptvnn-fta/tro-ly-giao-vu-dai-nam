# Dockerfile — Trợ lý Giáo vụ số Đại Nam (deploy lên Google Cloud Run)
# Chiến lược: chỉ cài DEPENDENCIES (không cài project thành package) rồi chạy app
# TỪ /app, để đường dẫn data/ (app/../data) phân giải đúng lúc chạy.

FROM python:3.11-slim

WORKDIR /app

# uv để cài deps nhanh
RUN pip install --no-cache-dir uv

# Cài dependencies production (khớp [project.dependencies] trong pyproject.toml)
RUN uv pip install --system --no-cache \
    "google-adk[gcp]>=2.0.0,<3.0.0" \
    "opentelemetry-instrumentation-google-genai>=0.1.0,<1.0.0" \
    "gcsfs>=2024.11.0" \
    "google-cloud-logging>=3.12.0,<4.0.0" \
    "flask>=3.0.0,<4.0.0" \
    "uvicorn>=0.30.0,<1.0.0"

# Mã nguồn + dữ liệu (bake vào image cho bản demo; production nên dùng CSDL/volume ngoài)
COPY app/ ./app/
COPY data/ ./data/
COPY frontend/ ./frontend/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

EXPOSE 8080

# Cloud Run truyền cổng qua biến $PORT. Chạy server ADK FastAPI (gồm web UI + /chat).
CMD ["sh", "-c", "uvicorn app.fast_api_app:app --host 0.0.0.0 --port ${PORT:-8080}"]
