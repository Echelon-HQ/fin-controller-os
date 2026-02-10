# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY controller /app/controller
COPY ui /app/ui
COPY orchestration /app/orchestration
COPY interface /app/interface
COPY config /app/config

# Create data directories
RUN mkdir -p /app/data/raw /app/data/processed /app/log

# Set Environment Variables
ENV PYTHONPATH=/app
ENV APP_HOME=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "controller/daily_run.py"]
