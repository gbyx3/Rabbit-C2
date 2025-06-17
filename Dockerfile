# Use a slim Python 3.11 base image for a lightweight container
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies, including Redis
RUN apt-get update && apt-get install -y \
    redis-server \
    && rm -rf /var/lib/apt/lists/*

# Define environment variable for Redis password
ENV REDIS_PASSWORD=CHANGEME

# Create Redis configuration file with the password from environment variable
RUN echo "requirepass $REDIS_PASSWORD" > /etc/redis/redis.conf

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir bottle redis requests

# Expose port 8000 for the Bottle application
EXPOSE 8000

# Start Redis with the custom configuration and run the Bottle application
CMD redis-server /etc/redis/redis.conf --daemonize yes && python server.py
