# Chemistry Dashboard

## User Setup Guide - Vagrant VM
### System Requirements
I believe any OS that can install Vagrant, Virtualbox, and Ansible should be good.

### Software Requirements
#### Git
#### Node.js
    https://nodejs.org
#### Python
    Python3
    Pip3
#### Angular:
    'npm install -g @angular/cli'
    'npm install -g node-gyp'
    If you're developing on OSX, you may also need to install XCode in order for node-sass to compile successfully.
#### VirtualBox (VM hypervisor)
    https://www.virtualbox.org/wiki/Downloads
#### Vagrant (VM deployment)
    https://wwww.vagrantup.com/donloads.html
#### Vagrant Plugins
    Don't believe we require any at this time, but we will for future AWS builds
#### Ansible (provisioning tool):
    'pip3 install ansible'

### Setup instructions

#### Client/Front-end
    Refer to client/README.md but keep in mind that the Angular compilation happens on the HOST (your actual local machine) instead of the Virtualbox VM since Vagrant deployed VMs share its working directory (local to Vagrantfile) by default.

    Assuming everything above has been successfully installed, all you should need to do is:
    'cd <project_directory>/client'
    'ng build --watch'

#### Server/Vagrant

     Navigate to the project source directory which contains ‘Vagrantfile’ and then run
    `vagrant up --provider virtualbox`

    For your first deployment, it will ask you which network interface to use for the VM’s bridged network.

    Once it’s deployed, the Vagrant setup will let you know the local IP address of your VM. You can copy this information to vagrant-user.yml in a fashion similar to my entries as a sample.

    You will also need to create your own web application user (the text at the end of the deployment should remind you to do so):

    ```
    'vagrant ssh'
    'source /var/lib/chemistry-dashboard/server/venv/bin/activate'
    'python3 /var/lib/chemistry-dashboard/server/create_user.py'
    'deactivate'
    ```

    The Discussion Capture web application should be available at your listed static IP.

## User Setup Guide - Manual
### System Requirements
Prefered OS: Ubuntu 16.04
Other versions of Ubuntu may work, but the installation script is only tested and verified on Ubuntu 16.04.5 LTS server.

### Install software
Navigate to the folder you would like to install Discussion Capture and perform the following commands.
Note: During the installtion, you will be asked to input a password for the root user for MySQL.  Please enter "root" as the password.
```
$ cd /var/lib
$ sudo https://github.com/tiilt-lab/chemistry-dashboard.git
$ cd chemistry-dashboard
$ sudo bash install.sh
```

You will then need to manually create the discussion capture database in MySQL...
```
$ mysql -u root -p
CREATE DATABASE discussion_capture;
exit
```

Once the database is created, it needs to be initialized.  Go to the chemistry-dashboard directory and enter the following...
```
source bin/activate
cd server
export FLASK_APP=discussion_capture.py
flask db upgrade
```

The database is initialized without any users, so you must create the first user for the system, who can then create other users from the UI. From the chemistry-dashboard directory...
```
sudo bin/python server/create_user.py
```

Finally, copy the json file provided to you for Google Cloud Services to ../chemistry-dashboard/audio_processing/asr_connectors/google-cloud-key.json
If a credentials file was not provided, please contact a team member for support.

NOTE: If the previous installation instructions fail, please follow maunal-install.md and report to a team member where the failure occurs.

### Accessing Discussion Capture's UI
After rebooting (and after completing installation successfully), you can access the dashboard by navigating in a browser to "http://server_ip", where server_ip is the ip of the server on the network.

To get the server ip, ssh (with 'vagrant ssh') into the server and enter...
'''
ifconfig
'''
All the ip addresses associated with the server should appear.

### Allow Access to ReSpeakers Connected by USB
```
$ sudo cp /opt/chemistry-dashboard/respeaker.rules /etc/udev/rules.d/.
$ sudo reboot
```

## Developer Setup Guide
The following guide is for developer use.  If you plan on making modifications to the code of Discussion Capture, please follow the instructions below.

### Audio Processing Service

The Audio Processing Service handles incoming socket connections containing raw audio data and outputs json formatted data related to the audio.
All the code for the Audio Processing Service can be found in 'chemistry-dashboard/audio_processing'.

The service should run automatically on boot.  For development purposes to manually start the server do the following:

```
$ sudo systemctl stop audio_processor
$ cd <yourpath>/chemistry-dashboard
$ source ./bin/activate
$ python3 audio_processing/server.py
```

### Discussion Capture Server

The server both serves the client UI and provides a REST API for accessing data stored by Discussion Capture for visualization in the client.
All the code for the server can be found in 'chemistry-dashboard/server'.
The server should run automatically on boot.  For development purposes to manually start the server, from vagrant (vagrant ssh) do the following:
```
$ sudo systemctl stop discussion_capture
$ source /var/lib/chemistry-dashboard/server/venv/bin/activate
$ python /var/lib/chemistry-dashboard/server/discussion_capture.py
```

Accessing a device's microphone is often times restricted to HTTPS traffic (local server runs on HTTP). To test BYOD functionality, many browsers require that you add your local server to a trusted source list.  To do this in chrome, place the following URL in your chrome address bar...

```
chrome://flags/#unsafely-treat-insecure-origin-as-secure
```

Then in the box below "Insecure origins treated as secure", add your local server's IP.  For example "http://192.168.1.101".
A relaunch button should then appear.  Clicking this will reboot the browser with your local server now treated as a trusted origin.


### Client
The client is an angular app which visualizes the discussion data and provides control over the system.
A prebuilt version of the angular client application is included with the repositiory, and will be used by the flask server by default.
All the code for the angular app can be found in 'chemistry-dashboard/client'.

If you are making modifications to the angular app, you will need to rebuild when files change.

For additional details on setting up and building the client, please see instructions [here](./client/README.md).
