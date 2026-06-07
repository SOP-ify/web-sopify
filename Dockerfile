# ── SOP-ify Web (Streamlit) ──────────────────────────────────────────────────
# Dockerfile untuk Cloud Run — tanpa GPU, base image ringan
#
# Build:
#   docker build -t sopify-web .
#
# Run lokal:
#   docker run -p 8501:8501 \
#     -e API_URL=http://localhost:8000 \
#     -e API_TOKEN=your_jwt_token \
#     sopify-web
#
# Cloud Run expose port 8501 (Streamlit default)

FROM python:3.10-slim

# env
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# install system deps minimal (audio libs untuk audio-recorder-streamlit)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# buat non-root user
RUN groupadd -r sopify && useradd -r -g sopify -d /app sopify

WORKDIR /app

# install python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# copy source
COPY --chown=sopify:sopify streamlit_demo.py .

# jalankan sebagai non-root
USER sopify

# expose streamlit port
EXPOSE 8501

# healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# entrypoint
CMD ["streamlit", "run", "streamlit_demo.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true", \
     "--browser.gatherUsageStats=false"]
