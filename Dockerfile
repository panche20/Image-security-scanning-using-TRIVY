# =========================
# Builder Stage
# =========================
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY app/requirements.txt .

RUN pip install --no-cache-dir \
    --prefix=/install \
    -r requirements.txt

COPY app/ .


# =========================
# Production Stage
# =========================
FROM python:3.11-slim AS production

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages

# Fix OS Vulnerabilities by upgrading base packages
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Copy dependencies
COPY --from=builder /install /usr/local

# Copy app
COPY --from=builder /app /app

# PURGE VULNERABLE VENDOR & LEGACY METADATA FOLDERS
RUN rm -rf /usr/local/lib/python3.11/site-packages/setuptools \
    && rm -rf /usr/local/lib/python3.11/site-packages/pip \
    && rm -rf /usr/local/lib/python3.11/site-packages/wheel-0.45.1.dist-info \
    && find /usr/local -type d -name "__pycache__" -exec rm -rf {} +

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]