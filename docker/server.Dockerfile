FROM python:3.9-slim
WORKDIR /var/lib/

# Install the application dependencies
RUN apt-get update && \
    apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl iputils-ping llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3 python3-pip python3-dev python3-venv python3-tk python3-openssl git pkg-config libfreetype6-dev libsndfile1
RUN mkdir -p chemistry-dashboard/server && \
    chmod 777 -R chemistry-dashboard

#Install Requirements
COPY server/requirements.txt /var/lib/chemistry-dashboard/requirements.txt
WORKDIR /var/lib/chemistry-dashboard/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    python -m spacy download en_core_web_sm

WORKDIR /var/lib/chemistry-dashboard/server

EXPOSE 5000 9001

HEALTHCHECK --start-period=2m --interval=5m --timeout=10s --retries=3 \
  CMD curl --include --no-buffer \
    --header "Connection: close" \
    --header "Upgrade: websocket" \
    http://127.0.0.1:5000

ENTRYPOINT ["./entry.sh"]

CMD ["python", "discussion_capture.py"]
