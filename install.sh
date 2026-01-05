#!/bin/bash

# Git should already be installed to clone the repo
# Otherwise download it via curl or wget

# Root is required
if [[ $EUID -ne 0 ]]; then
	echo "Error: This script must be run as root."
	exit 1
fi

# Install all updates and the required components
echo "Updating OS and installing required components"
apt update
apt upgrade -y
apt install -y mplayer ffmpeg

# Make the files executable and put them in /usr/local/bin
echo "Copying files"
chmod +x play-music server.py pause next prev track
cp play-music server.py pause next prev track /usr/local/bin/

# Make the web directory and move index.html
mkdir -p /var/www/html
cp index.html /var/www/html

# Set the web GUI and play-music scripts to start on reboot by adding them to cron
NEW_JOB1="@reboot python3 /usr/local/bin/server.py > /dev/null 2>&1 &"
NEW_JOB2="@reboot /usr/local/bin/play-music &"

# Add the job only if it doesn't already exist
(crontab -l 2>/dev/null; echo "$NEW_JOB1") | sort -u | crontab -
(crontab -l 2>/dev/null; echo "$NEW_JOB2") | sort -u | crontab -