FROM python:3.9-slim
WORKDIR /var/lib/

# Install the application dependencies
RUN apt-get update
RUN apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl iputils-ping llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3 python3-pip python3-dev python3-venv python3-tk python3-openssl git pkg-config libfreetype6-dev libsndfile1
RUN mkdir -p chemistry-dashboard/server

#Create processor folder
COPY server chemistry-dashboard/server
RUN chmod 777 -R chemistry-dashboard

COPY server/requirements.txt /var/lib/chemistry-dashboard/requirements.txt
WORKDIR /var/lib/chemistry-dashboard/

#Install Requirements
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m spacy download en_core_web_sm

COPY server server
WORKDIR /var/lib/chemistry-dashboard/server

EXPOSE 5000 9001

RUN chmod +x entry.sh

HEALTHCHECK --start-period=2m --interval=30s --timeout=10s --retries=3 \
  CMD ping -c 3 audio_processor || exit 1

ENTRYPOINT ["./entry.sh"]

CMD ["python", "discussion_capture.py"]
