FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py ./main.py
COPY scraper/ ./scraper/
COPY assistant/ ./assistant/

# Create data directories
RUN mkdir -p data/articles logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Default command: daily scraper/uploader job
CMD ["python", "main.py"]
