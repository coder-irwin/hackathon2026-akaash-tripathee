FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies if required and clean up
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure necessary output files exist to avoid permission issues
RUN touch audit_log.json outbound_queue.json && \
    chmod 666 audit_log.json outbound_queue.json

# Expose port 5000 for the Flask dashboard
EXPOSE 5000

# Healthcheck to ensure the dashboard is alive
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Start the dashboard by default
CMD ["python", "dashboard.py"]
