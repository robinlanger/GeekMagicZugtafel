FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chmod=755 zugtafel ./zugtafel

RUN useradd --system --uid 1000 zugtafel
USER zugtafel

ENV PYTHONUNBUFFERED=1 TZ=Europe/Berlin
CMD ["python", "-m", "zugtafel"]
