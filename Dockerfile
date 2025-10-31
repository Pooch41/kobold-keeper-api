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
RUN apt-get update && \
    apt-get install -y --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create dedicated non-root user and group for security
RUN groupadd -r django && useradd -r -g django django

COPY render_web_entrypoint.sh /usr/local/bin/render_web_entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/render_web_entrypoint.sh && \
    chmod +x /usr/local/bin/render_web_entrypoint.sh


COPY . /app/


COPY ./api/dice_roller.py /app/api/dice_roller.py
COPY ./api/serializers.py /app/api/serializers.py
COPY ./api/views.py /app/api/views.py
COPY ./api/dice_reader.py /app/api/dice_reader.py


# Set file ownership for non-root user access
RUN chown -R django:django /app && \
    chown django:django /usr/local/bin/render_web_entrypoint.sh

# Switch to the non-root user
USER django

# Stage 3: Container Entrypoint
# Execute the custom startup script
CMD ["/usr/local/bin/start.sh"]
