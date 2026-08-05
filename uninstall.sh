#!/bin/bash

echo "Uninstalling Discussion Capture..."
sudo systemctl stop audio_processor
sudo systemctl stop discussion_capture
sudo systemctl disable audio_processor
sudo systemctl disable discussion_capture
sudo rm /lib/systemd/system/audio_processor.service
sudo rm /lib/systemd/system/discussion_capture.service
echo "Discussion Capture uninstalled successfully! You may now delete the chemistry-dashboard folder."
