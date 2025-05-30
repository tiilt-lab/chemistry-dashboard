FROM amazonlinux:latest
WORKDIR /var/lib/

# Install the application dependencies
RUN yum update && \
    yum install --allowerasing -y make gcc gcc-c++ make glibc-devel openssl-devel zlib-devel bzip2-libs readline-devel sqlite-devel wget curl iputils llvm ncurses-devel libffi libffi-devel xz-devel python3 python3-pip python3-devel openssl-devel python3-tkinter git pkg-config mesa-libGL-devel freetype-devel libsndfile
RUN curl -O https://bootstrap.pypa.io/get-pip.py && \
    python3 get-pip.py --user

#Setup folders
RUN mkdir -p chemistry-dashboard/audio_processing && \
    chmod 777 -R chemistry-dashboard

#Install Requirements
COPY audio_processing/requirements.txt /var/lib/chemistry-dashboard/requirements.txt
WORKDIR /var/lib/chemistry-dashboard/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir spacy && \
    python3 -m spacy download en_core_web_sm && \
    pip install --no-cache-dir wheel && \
    pip install --use-pep517 --no-cache-dir -r requirements.txt

# Audio processing port
EXPOSE 9000

HEALTHCHECK --start-period=2m --interval=5m --timeout=10s --retries=3 \
  CMD curl --include --no-buffer \
    --header "Connection: close" \
    --header "Upgrade: websocket" \
    http://127.0.0.1:9000

CMD ["python3", "audio_processing/server.py"]
