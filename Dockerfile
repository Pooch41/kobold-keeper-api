# Stage 1: Base Image and Environment Setup
FROM python:3.11-slim

# Environment setup for optimal Python execution
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=kobold_keeper.settings

# Set application working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt /app/

# Stage 2: Dependencies, Installation, and Security
# Install netcat (for waiting on DB in start.sh) and clean up apt cache
RUN apt-get update && \
    apt-get install -y netcat-openbsd --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create dedicated non-root user and group for security
RUN groupadd -r django && useradd -r -g django django

# Copy startup script and fix line endings (for Windows compatibility)
COPY start.sh /usr/local/bin/start.sh
RUN sed -i 's/\r$//' /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Copy the entire project
COPY . /app/

# Set file ownership for non-root user access
RUN chown -R django:django /app
RUN chown django:django /usr/local/bin/start.sh

# Switch to the non-root user
USER django

# Stage 3: Container Entrypoint
# Execute the custom startup script (will be overridden by worker/beat)
CMD ["/usr/local/bin/start.sh"]