#!/bin/bash

# Git should already be installed to clone the repo
# Otherwise download it via curl or wget

# Root is required
if [[ $EUID -ne 0 ]]; then
	echo "Error: This script must be run as root."
	exit 1
fi

# Get the path to me
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

source $SCRIPT_DIR/.env

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
chmod +x buddybox buddyboxUI.py logger bb-pause bb-next bb-prev bb-fade bb-lock bb-track
cp buddybox buddyboxUI.py .env logger bb-pause bb-next bb-prev bb-fade bb-lock bb-track /usr/local/bin/

# Make the web directory and copy index.html to it
mkdir -p /var/www/html
cp -r index.html icons /var/www/html/

echo "Adding cron jobs..."
# Set the web GUI and play-music scripts to start on reboot by adding them to cron
CRON_JOB1='@reboot echo "$(date "+\%Y-\%m-\%d \%H:\%M:\%S") ----- System Rebooted -----" >> "'$LOGFILE'"'
CRON_JOB2="@reboot /usr/local/bin/buddyboxUI.py > /dev/null 2>&1 &"
CRON_JOB3="@reboot /usr/local/bin/buddybox &"

# Add the job only if it doesn't already exist
(crontab -l 2>/dev/null; echo "$CRON_JOB1") | sort -u | crontab -
(crontab -l 2>/dev/null; echo "$CRON_JOB2") | sort -u | crontab -
(crontab -l 2>/dev/null; echo "$CRON_JOB3") | sort -u | crontab -

echo ""
echo "Installation complete. Music will start on reboot, unless lockout is enabled (see README)."
echo ""
read -p "Start playback now (without rebooting)? [y/N]: " choice

choice="${choice:-n}"
choice=$(echo "$choice" | tr '[:upper:]' '[:lower:]')

if [ "$choice" = "y" ]; then
        echo "Starting playback..."
        buddybox & buddyboxUI.py > /dev/null 2>&1 &
fi
