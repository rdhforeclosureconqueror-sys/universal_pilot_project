FROM python:3.12

# Set working directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Command to run Alembic (optional default)
EXPOSE 8000
CMD ["sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
