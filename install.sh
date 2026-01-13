#!/bin/bash

# Git should already be installed to clone the repo
# Otherwise download it via curl or wget

# Root is required
if [[ $EUID -ne 0 ]]; then
	echo "Error: This script must be run as root."
	exit 1
fi

read -p "Install all available updates? [y/N]: " choice

choice="${choice:-n}"
choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')

if [ "$choice" = "y" ]; then
	echo "Updating OS..."
	apt update
	apt upgrade -y
fi

# Install required components
echo "Installing required components..."
apt install -y mpv ffmpeg socat bc jq

# Make the files executable and copy them to /usr/local/bin
echo "Copying files"
chmod +x buddybox buddyboxUI.py bb-pause bb-next bb-prev bb-fade bb-track
cp buddybox buddyboxUI.py bb-pause bb-next bb-prev bb-fade bb-track /usr/local/bin/

# Make the web directory and copy index.html to it
mkdir -p /var/www/html
cp index.html /var/www/html

# Set the web GUI and play-music scripts to start on reboot by adding them to cron
NEW_JOB1="@reboot /usr/local/bin/buddyboxUI.py > /dev/null 2>&1 &"
NEW_JOB2="@reboot /usr/local/bin/buddybox &"

# Add the job only if it doesn't already exist
(crontab -l 2>/dev/null; echo "$NEW_JOB1") | sort -u | crontab -
(crontab -l 2>/dev/null; echo "$NEW_JOB2") | sort -u | crontab -

echo "Installation complete. Reboot to start playing or run this command:"
echo
echo "buddybox & buddyboxUI.py > /dev/null 2>&1 &"
