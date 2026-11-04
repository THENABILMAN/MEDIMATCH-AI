# Build context is the repository root: docker build -f backend/Dockerfile .
FROM python:3.12-slim AS build
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /venv
COPY backend/requirements.txt .
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PATH=/venv/bin:$PATH
RUN useradd --create-home --uid 10001 medimatch
COPY --from=build /venv /venv
WORKDIR /srv/backend
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY supabase/migrations /srv/supabase/migrations
USER medimatch
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]
# Exec form, so uvicorn receives SIGTERM and finishes running work
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--timeout-graceful-shutdown", "30"]
