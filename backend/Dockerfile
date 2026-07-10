FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --default-timeout=1000 -r requirements.txt
COPY . .
ENV HF_HUB_DISABLE_XET=1
ENV HF_HUB_DOWNLOAD_TIMEOUT=120
ENV FASTEMBED_CACHE=/app/.fastembed_cache
# Split into separate RUN layers so a transient network failure on one model
# doesn't force a redownload of the others on retry.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5', cache_dir='${FASTEMBED_CACHE}')"
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='Qdrant/clip-ViT-B-32-text', cache_dir='${FASTEMBED_CACHE}')"
RUN python -c "from fastembed import ImageEmbedding; ImageEmbedding(model_name='Qdrant/clip-ViT-B-32-vision', cache_dir='${FASTEMBED_CACHE}')"
RUN python -c "from fastembed.rerank.cross_encoder import TextCrossEncoder; TextCrossEncoder(model_name='Xenova/ms-marco-MiniLM-L-6-v2', cache_dir='${FASTEMBED_CACHE}')"
RUN python -c "from fastembed import SparseTextEmbedding; SparseTextEmbedding(model_name='Qdrant/bm25', cache_dir='${FASTEMBED_CACHE}')"
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/figures \
    && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
# HF Spaces (Docker SDK) sets PORT=7860 and expects the app to listen on it;
# local docker-compose leaves PORT unset, so this defaults to 8000.
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
