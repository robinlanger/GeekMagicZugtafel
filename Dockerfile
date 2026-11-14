FROM mcr.microsoft.com/playwright/python:v1.65.2-noble

# Layout mirrors the repo so glancebox.__version__ finds /app/VERSION (parents[2] of the package).
WORKDIR /app
COPY --chown=pwuser VERSION ./VERSION
COPY --chown=pwuser server ./server
COPY --chown=pwuser pages ./pages

# Editable install keeps the package at /app/server/glancebox. requirements.lock also pulls in
# the dev tools (pytest, ...) so `pytest -m browser` can run inside this image.
RUN pip install --no-cache-dir --break-system-packages -r server/requirements.lock \
 && pip install --no-cache-dir --break-system-packages --no-deps -e server

ENV PYTHONUNBUFFERED=1 \
    TZ=Europe/Berlin \
    GLANCEBOX_PAGES_DIR=/app/pages

# The base image already ships a non-root user (pwuser) and the browsers.
USER pwuser
WORKDIR /app/server

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8080/healthz', timeout=4)"

CMD ["python", "-m", "glancebox", "serve"]
