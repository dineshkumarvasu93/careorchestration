# Backend image for the Care Orchestration API.
# Uses Python 3.12 for broad wheel availability (psycopg, SQLAlchemy).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY requirements.txt requirements-docker.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt -r requirements-docker.txt

# Application code.
COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
