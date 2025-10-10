FROM python:3.13-slim

# Install system dependencies, Chromium and Chromedriver for Selenium
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       chromium \
       chromium-driver \
       fonts-liberation \
       ca-certificates \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Environment variables for Chromium in Selenium
ENV CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER=/usr/bin/chromedriver \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python dependencies first (better layer caching)
COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install gunicorn

# Copy application code
COPY . .

# Create non-root user to run the app
RUN useradd -m appuser \
    && chown -R appuser:appuser /app \
    && mkdir -p /app/app/config \
    && chmod 755 /app/app/config
USER appuser

# Expose application port
EXPOSE 8000

# Gunicorn config and start command
CMD ["gunicorn", "-c", "gunicorn.conf.py", "run:app"]


