# Chemistry Dashboard

## Docker Development Environment Setup

### Check configuration

Checkout the development branch and create and new branch for your feature

```
git pull or git clone ...
git checkout dev
git checkout -b your_feature_branch_name

```

Check server/config.ini

```
https=false
debug=true
domain=127.0.0.1
```

Check server/app.py

```
...
redis_loc = "redis://redis:6379"
...
DATABASE_SERVER = "blinc-db"
...

```

Check audio_processing/config.ini

```
processing_callback=http://server:5000/api/v1/callback/transcript
connect_callback=http://server:5000/api/v1/callback/connect
disconnect_callback=http://server:5000/api/v1/callback/disconnect
tagging_callback=http://server:5000/api/v1/callback/tag
speaker_metrics_callback=http://server:5000/api/v1/callback/speaker_transcript_metrics
```

Check deploy/nginx.conf

```
events {}
http {
  ...
  upstream api{
    server server:5000;
  }
  ...
}
```

### Install Dependencies

Download and Install Docker Hub for your device

```
https://hub.docker.com/welcome
```

Download the current google-cloud-key.json and place in audio_processing/asr_connectors

### Run Docker Containers

Will take some time the first time depending on hardware

```
docker compose -f 'compose.yaml' up -d --build 
```

After sucessful build, access server at http://127.0.0.1

### Docker Hub

You should be able to see the container in docker hub in a single compose stack called chemistry-dashboard. Here you can validate the containers are running. To develop, perform changes in the local files then rebuild the containers to view the changes at the server location above.

### Rebuilding Containers

Rerun the docker compose above to rebuild all containers to see changes. To build specific containers when only a single component needs to be rebuilt due to changes:

```
docker compose -f 'compose.yaml' up -d --build 'container-name'

e.g. docker compose -f 'compose.yaml' up -d --build 'nginx'
```

If frontend changes aren't being seen, delete the nginx container in docker hub to force the rebuild of that container when running the compose. 

### Not enough Stroage 

If the audio_processor at 20GB is too large to store directly on your computer, use an external drive which can be setup with docker following the directions below:

```
https://www.howtogeek.com/devops/how-to-store-docker-images-and-containers-on-an-external-drive/
```

## Hosted Server Setup
### Installing Dependencies

Update system packages

```
sudo apt-get update
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python3 python3-pip python3-dev python3-venv python3-tk python3-openssl git sqlite nginx pkg-config libfreetype6-dev libsndfile1
```

Install pyenv

```
curl https://pyenv.run | bash

```

Follow install instructions at end of install to add to path which most likely says:

```
WARNING: seems you still have not added 'pyenv' to the load path.

Load pyenv automatically by adding
the following to ~/.bashrc:

export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
```

Restart the Shell

```
exec "$SHELL"
```

Install Redis

```
sudo apt-get install redis-server
sudo systemctl enable redis-server.service
```

Installing MySQL server. When asked to provide a root password, enter "root" as the password.

```
sudo apt-get install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

## For Video Processing (Optional):

Install nvidia driver, cuda, and cudnn for ubuntu version 22.04

Install nvidia driver (if it is not already installed)

```
sudo ubuntu-drivers list --gpgpu
You should see a list such as the following:
    nvidia-driver-418-server
    nvidia-driver-515-server
    nvidia-driver-525-server
    nvidia-driver-450-server
    nvidia-driver-515
    nvidia-driver-525
choose the version that is annotated recommended
lets assume version 525 is the recommended version then you run
sudo ubuntu-drivers install nvidia:525
```

Install cuda

```
visit https://developer.nvidia.com/cuda-12-1-0-download-archive and select the option that fits your architecture
However, if you are seting this up for ubuntu 22.04, run these commands

$ wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
$ sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
$ wget https://developer.download.nvidia.com/compute/cuda/12.1.0/local_installers/cuda-repo-ubuntu2204-12-1-local_12.1.0-530.30.02-1_amd64.deb
$ sudo dpkg -i  cuda-repo-ubuntu2204-12-1-local_12.1.0-530.30.02-1_amd64.deb
$ sudo cp /var/cuda-repo-ubuntu2204-12-1-local/cuda-*-keyring.gpg /usr/share/keyrings/
$ sudo apt-get update
$ sudo apt-get -y install cuda
```

Install cudnn for ubuntu 22.04

```
$ wget https://developer.nvidia.com/downloads/compute/cudnn/secure/8.8.1/local_installers/12.0/cudnn-local-repo-ubuntu2204-8.8.1.3_1.0-1_amd64.deb

$ sudo apt install cudnn-local-repo-ubuntu2204-8.8.1.3_1.0-1_amd64.deb
$ sudo cp /var/cudnn-local-repo-ubuntu2204-8.8.1.3/cudnn-local-*-keyring.gpg /usr/share/keyrings/
```

Finally, to verify the installation, check

```
$ nvidia-smi
$ nvcc -V
```

```
cd ../../../video_processing
python3 -m venv ./venv
source venv/bin/activate

pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip3 install cmake matplotlib ninja numpy opencv-python scipy tqdm wget imutils

install dlib with cuda enabled

$ git clone https://github.com/davisking/dlib.git
$ cd dlib
$ mkdir build
$ cd build
$ cmake .. -D DLIB_USE_CUDA=1 -D USE_AVX_INSTRUCTIONS=1 -D CMAKE_C_COMPILER=/usr/bin/gcc-11
$ cmake --build .
$ cd ..
$ python setup.py install --set DLIB_USE_CUDA=1 --set CMAKE_C_COMPILER=/usr/bin/gcc-11
```

## Required parts of Server:

Create a database in MySQL

```
sudo mysql -u root -p
CREATE DATABASE discussion_capture;
CREATE USER 'vagrant'@'localhost' IDENTIFIED BY 'vagrant';
GRANT ALL PRIVILEGES ON discussion_capture.* TO 'vagrant'@'localhost';
FLUSH PRIVILEGES;
exit
```

Go to var/lib foloder and pull the git repo

```
cd /var/lib/
sudo git clone https://github.com/tiilt-lab/chemistry-dashboard.git
sudo chmod 777 -R chemistry-dashboard
cd chemistry-dashboard
```

Create python3 virtual environments with pyenv and install packages.

```
pyenv install 3.9.21

cd server
pyenv virtualenv 3.9.21 discussion_capture
pyenv local discussion_capture
pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
pyenv which python
cd ..
```

Change ExecStart of deploy/discussion_capture.service with "pyenv which python" result above

```
cd audio_processing
pyenv virtualenv 3.9.21 audio_processor
pyenv local audio_processor
pip install --upgrade pip
pip install spacy
python -m spacy download en_core_web_sm
pip install wheel
pip install -r requirements.txt
pyenv which python
cd ..
```

Change ExecStart of deploy/audio_processor.service with "pyenv which python" result above

Fetch audio processing service models.
NOTE: Perfom from chemistry-dashboard root directory.

```
mkdir -p audio_processing/keyword_detector/models
```

Then call the following line to download Google News Vectors

```
cd audio_processing/keyword_detector/models
pip install gdown
gdown https://drive.google.com/uc?id=0B7XkCwpI5KDYNlNUTTlSS21pQmM

```
After the download is complete, execute the following lines.

```
gunzip GoogleNews-vectors-negative300.bin.gz
```

Setup the flask app

```
cd ../server
export FLASK_APP=discussion_capture.py
flask db upgrade
```

Then setup up the front-end by following the README in the frontend folder, chemistry-dashboard/frontend

Setup Discussion Capture system services.

```
sudo cp deploy/discussion_capture.service /lib/systemd/system/discussion_capture.service
sudo cp deploy/audio_processor.service /lib/systemd/system/audio_processor.service
sudo cp deploy/video_processor.service /lib/systemd/system/video_processor.service
sudo systemctl enable discussion_capture
sudo systemctl enable audio_processor
sudo systemctl enable video_processor
```

Setup Nginx.

```
sudo cp deploy/nginx.conf /etc/nginx/nginx.conf
sudo cp deploy/nginx-headers.conf /etc/nginx/nginx-headers.conf
sudo nginx -s reload

```
