FROM python:3.12-slim

# Install system dependencies and Stockfish
RUN apt-get update && apt-get install -y \
    stockfish \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# EXPOSE is documented, but Render overrides this with the $PORT env var
EXPOSE 8000

# Shell form evaluates the runtime $PORT variable correctly on Render
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
