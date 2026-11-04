FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-eval.txt ./
RUN pip install --default-timeout=1000 -r requirements.txt
# The evaluation harness needs Ragas and friends; build with
#   --build-arg EXTRA_REQUIREMENTS=requirements-eval.txt   (docker compose does this for the "eval" service)
ARG EXTRA_REQUIREMENTS=""
RUN if [ -n "$EXTRA_REQUIREMENTS" ]; then pip install --default-timeout=1000 -r "$EXTRA_REQUIREMENTS"; fi
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
