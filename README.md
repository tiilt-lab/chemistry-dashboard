# Chemistry Dashboard

Update system packages
```
sudo apt-get update
sudo apt-get install python python3 python3-pip python3-dev python3-venv python3-tk git sqlite nginx pkg-config libfreetype6-dev libsndfile1
```

Install Redis
```
sudo apt-get install redis-server
sudo systemctl enable redis-server.service
```

Installing MySQL server.  When asked to provide a root password, enter "root" as the password.
```
sudo apt-get install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
```

Install nvidia driver, cuda, and cudnn for ubuntu version 22.04

Install nvidia driver  (if it is not already installed)
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
# Finally, to verify the installation, check
nvidia-smi
nvcc -V

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
chmod 777 -R chemistry-dashboard
cd chemistry-dashboard
```


Create python3 virtual environment and install packages.
```
cd server
python3 -m venv ./venv
source venv/bin/activate
pip3 install -r requirements.txt
deactivate
cd ..

cd audio_processing
python3 -m venv ./venv
source venv/bin/activate
pip3 install spacy
python3 -m spacy download en_core_web_sm
pip3 install wheel
pip3 install -r requirements.txt
deactivate
cd ..
```
Fetch audio processing service models.
NOTE: Perfom from chemistry-dashboard root directory.
```
mkdir -p audio_processing/keyword_detector/models
```
Then call the following line
```
cd audio_processing/keyword_detector/models
wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=0B7XkCwpI5KDYNlNUTTlSS21pQmM' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=0B7XkCwpI5KDYNlNUTTlSS21pQmM" -O GoogleNews-vectors-negative300.bin.gz && rm -rf /tmp/cookies.txt
```
After the download is complete, execute the following lines.
```
gunzip GoogleNews-vectors-negative300.bin.gz
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
Setup the flask app
```
cd ../server
source venv/bin/activate
export FLASK_APP=discussion_capture.py
flask db upgrade
```

Then setup up the front-end by following the README in the client folder, chemistry-dashboard/client

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
