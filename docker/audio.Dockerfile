FROM python:3.9-slim
WORKDIR /var/lib/

# Install the application dependencies
RUN apt-get update && \
    apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl iputils-ping llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3 python3-pip python3-dev python3-venv python3-tk python3-openssl git pkg-config libfreetype6-dev libsndfile1

#Setup folders
RUN mkdir -p chemistry-dashboard/audio_processing && \
    chmod 777 -R chemistry-dashboard

#Install Requirements
COPY audio_processing/requirements.txt /var/lib/chemistry-dashboard/requirements.txt
WORKDIR /var/lib/chemistry-dashboard/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir spacy && \
    python -m spacy download en_core_web_sm && \
    pip install --no-cache-dir wheel && \
    pip install --no-cache-dir -r requirements.txt

# Audio processing port
EXPOSE 9000

HEALTHCHECK --start-period=2m --interval=30s --timeout=10s --retries=3 \
  CMD ping -c 3 server || exitgt 1

CMD ["python", "audio_processing/server.py"]
