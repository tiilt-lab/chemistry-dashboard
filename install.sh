#!/bin/bash

echo "Installing Discussion Capture..."

echo "Updating system packages..."
sudo apt-get update
sudo apt-get install python3 python3-pip python3-dev python3-venv python3-tk git nginx
echo "Packages updated."

echo "Installing Redis..."
sudo apt-get install redis-server
sudo systemctl enable redis-server.service
echo "Redis installed."

echo "Installing MySQL server..."
sudo apt-get install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
echo "MySQL server installed."

echo "Creating python3 venv for DC server..."
cd server
python3 -m venv ./venv
source venv/bin/activate
pip3 install -r requirements.txt
deactivate
cd ..
echo "Python3 venv setup complete."

echo "Creating python3 venv for audio processing service..."
cd audio_processing
python3 -m venv ./venv
source venv/bin/activate
pip3 install -r requirements.txt
deactivate
cd ..
echo "Python3 venv setup complete."

echo "Fetching audio processing service models...this may take a while..."
echo "Fetching Google Word2Vec model..."
mkdir -p audio_processing/keyword_detector/models
OUTPUT=$( wget --save-cookies cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=0B7XkCwpI5KDYNlNUTTlSS21pQmM' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/Code: \1\n/p' )
CODE=${OUTPUT##*Code: }
wget --load-cookies cookies.txt 'https://docs.google.com/uc?export=download&confirm='$CODE'&id=0B7XkCwpI5KDYNlNUTTlSS21pQmM' -O 'audio_processing/keyword_detector/models/GoogleNews-vectors-negative300.bin.gz'
rm cookies.txt
echo "Unpacking Google Word2Vec model..."
gunzip audio_processing/keyword_detector/models/GoogleNews-vectors-negative300.bin.gz
echo "Audio processing serivce models installed."

echo "Setting up Discussion Capture system services..."
sudo cp deploy/discussion_capture.service /lib/systemd/system/discussion_capture.service
sudo cp deploy/audio_processor.service /lib/systemd/system/audio_processor.service
sudo systemctl enable discussion_capture
sudo systemctl enable audio_processor
echo "Discussion Capture system services setup."

echo "Setting up nginx..."
sudo cp deploy/nginx.conf /etc/nginx/nginx.conf
sudo cp deploy/nginx-headers.conf /etc/nginx/nginx-headers.conf
sudo nginx -s reload
echo "nginx setup complete."

echo "Installation complete!  Please reboot your system"
