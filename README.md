# Chemistry Dashboard

Update system packages
```
sudo apt-get update
sudo apt-get install python3 python3-pip python3-dev python3-venv python3-tk git sqlite nginx pkg-config libfreetype6-dev libsndfile1
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
python3 -m spacy download en
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
wget https://s3.amazonaws.com/dl4j-distribution/GoogleNews-vectors-negative300.bin.gz
```
After the download is complete, execute the following lines.
```
gunzip GoogleNews-vectors-negative300.bin.gz
```

Setup the flask app
```
cd ../../../server
source venv/bin/activate
export FLASK_APP=discussion_capture.py
flask db upgrade
```

Then setup up the front-end by following the README in the client folder, chemistry-dashboard/client

Setup Discussion Capture system services.
```
sudo cp deploy/discussion_capture.service /lib/systemd/system/discussion_capture.service
sudo cp deploy/audio_processor.service /lib/systemd/system/audio_processor.service
sudo systemctl enable discussion_capture
sudo systemctl enable audio_processor
```

Setup Nginx.
```
sudo cp deploy/nginx.conf /etc/nginx/nginx.conf
sudo cp deploy/nginx-headers.conf /etc/nginx/nginx-headers.conf
sudo nginx -s reload

```
