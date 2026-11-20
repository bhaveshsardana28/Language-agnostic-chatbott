FROM python:3.12.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-osd \
        tesseract-ocr-hin \
        tesseract-ocr-pan \
        tesseract-ocr-spa \
        tesseract-ocr-fra \
        tesseract-ocr-deu \
        tesseract-ocr-ita \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements.lock ./
# The Linux PyPI torch build pulls a large CUDA stack. The app only needs CPU
# inference for local multilingual embeddings, so seed the CPU wheel first;
# the locked install below reuses this exact version without downloading CUDA.
RUN python -m pip install --no-cache-dir pip==26.2.1
RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu --no-deps torch==2.14.1
RUN python -m pip install --no-cache-dir -r requirements.lock
COPY app.py config.py ./
COPY src/ src/
COPY backend/ backend/
COPY static/ static/
COPY templates/ templates/
RUN useradd --create-home --uid 10001 gaia \
    && mkdir -p data/uploads cache logs \
    && chown -R gaia:gaia data cache logs \
    && chmod 700 data data/uploads cache logs
USER gaia

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
