FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create output dirs
RUN mkdir -p experiments/charts/multicore
RUN mkdir -p experiments/charts

# Expose port
EXPOSE 8080

# Default: run metrics server (covers both single + multi core)
CMD ["python", "metrics/metrics_server.py"]