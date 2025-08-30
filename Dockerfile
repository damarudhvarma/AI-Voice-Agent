# Dockerfile for AI Voice Agent - Alternative deployment method
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY server/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . /app

# Set Python path
ENV PYTHONPATH=/app/server

# Change to server directory
WORKDIR /app/server

# Create uploads directory
RUN mkdir -p uploads

# Expose port
EXPOSE $PORT

# Set default port
ENV PORT=10000

# Start the application
CMD ["python", "app_refactored.py"]
