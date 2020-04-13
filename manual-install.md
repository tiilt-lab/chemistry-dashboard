# Chemistry Dashboard

Update system packages
```
sudo apt-get update
sudo apt-get install python3 python3-pip python3-dev python3-venv git sqlite
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

Create a database in MySQL
```
mysql -u root -p
CREATE DATABASE discussion_capture;
exit
```

Create python3 virtual environment and install packages.
```
cd <directory-where-you-want-discussion-capture>
git clone https://bitbucket.org/acropolis-athens/chemistry-dashboard
cd chemistry-dashboard
python3 -m venv ./
source bin/activate
pip3 install -r requirements.txt
pip3 install --upgrade google-cloud-speech
deactivate
```

Install angular and build the UI.
Follow the the "Setup" section of the README.md in the client folder.

Fetch audio processing service models.
NOTE: Perfom from chemistry-dashboard directory.
```
mkdir -p audio_processing/keyword_detector/models
```
Then call the following line and take note of the code that is output ("Code: ####").
```
wget --save-cookies cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=0B7XkCwpI5KDYNlNUTTlSS21pQmM' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/Code: \1\n/p'
```
Using the code from the previous step, call the following line where "CODE" is the code you received.
```
wget --load-cookies cookies.txt 'https://docs.google.com/uc?export=download&confirm='CODE'&id=0B7XkCwpI5KDYNlNUTTlSS21pQmM' -O 'audio_processing/keyword_detector/models/GoogleNews-vectors-negative300.bin.gz'
```
After the download is complete, execute the following lines.
```
rm cookies.txt
gunzip audio_processing/keyword_detector/models/GoogleNews-vectors-negative300.bin.gz
```

Setup Discussion Capture system services.
```
sudo cp discussion_capture.service /lib/systemd/system/discussion_capture.service
sudo cp audio_processor.service /lib/systemd/system/audio_processor.service
sudo systemctl enable discussion_capture
sudo systemctl enable audio_processor
```

Setup Nginx.
```
sudo cp deploy/nginx.conf /etc/nginx/nginx.conf
sudo cp deploy/nginx-headers.conf /etc/nginx/nginx-headers.conf
sudo nginx -s reload
```