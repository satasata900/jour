FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN for i in 1 2 3 4 5; do \
      pip install --no-cache-dir --timeout 600 --retries 10 --progress-bar off -r requirements.txt && break; \
      echo "pip install failed (attempt $i), retrying in 5s..."; \
      sleep 5; \
    done

COPY . ./

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
