FROM python:3.11-slim

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE kobold_keeper.settings

WORKDIR /app

COPY requirements.txt /app/

RUN apt-get update && \
    apt-get install -y netcat-openbsd --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd -r django && useradd -r -g django django

COPY start.sh /usr/local/bin/start.sh


RUN sed -i 's/\r$//' /usr/local/bin/start.sh

RUN chmod +x /usr/local/bin/start.sh

COPY . /app/

RUN chown -R django:django /app
RUN chown django:django /usr/local/bin/start.sh

USER django


CMD ["/usr/local/bin/start.sh"]
