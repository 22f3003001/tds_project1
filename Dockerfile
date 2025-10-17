FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY code_generator.py .
COPY github_manager.py .
COPY evaluator.py .

# Expose port (Hugging Face uses 7860)
EXPOSE 7860

# Set environment variables
ENV PORT=7860
ENV PYTHONUNBUFFERED=1

# Run with gunicorn for production
CMD gunicorn --bind 0.0.0.0:7860 --workers 2 --threads 4 --timeout 600 app:app
