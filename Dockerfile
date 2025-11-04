FROM python:3.12.10-slim

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies
RUN apt-get purge -y --auto-remove \
    gcc \
    build-essential
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    ca-certificates \
  && wget -qO- https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-linux-signing-keyring.gpg \
  && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
  && apt-get update && apt-get install -y --no-install-recommends \
    google-chrome-stable \
    fonts-liberation \
  && rm -rf /var/lib/apt/lists/*

COPY . .

ENV FLASK_APP=run.py
ENV WORKERS=2
ENV THREADS=4
ENV TIMEOUT=900
ENV PORT=7878

CMD ["sh", "-c", "gunicorn -w $WORKERS --threads $THREADS -t $TIMEOUT --bind 0.0.0.0:$PORT run:app"]