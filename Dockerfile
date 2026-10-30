# syntax=docker/dockerfile:1.7
# Multi-stage build: dependencies are compiled once, the runtime image carries
# only the virtual environment and runs as an unprivileged user.
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .

FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="adaptedge" \
      org.opencontainers.image.description="Adaptive WebRTC/QUIC transport selection replay harness" \
      org.opencontainers.image.source="https://github.com/Erixest/adaptedge" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="0.1.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY --chown=app:app src ./src
COPY --chown=app:app data ./data

USER app
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

ENTRYPOINT ["uvicorn", "adaptedge.api:app", "--host", "0.0.0.0", "--port", "8000"]
