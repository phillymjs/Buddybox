# Buddybox

Much-improved version of a Raspberry Pi-based music player I first created in 2017.

### Background

I used to keep a radio playing to keep my pet birds company when I'm not in the room with them or not at home. Over time, I got absolutely sick to death of hearing the same two dozen or so songs, and the ads were constant and obnoxious. I set out to make a simple, self-contained music player that would only play songs I liked. Since I thought of it as a jukebox and the bird I had at the time was named Buddy, I called the project Buddybox.

The current version is built on mpv, but the original was built upon mplayer. There was a little more to it even in the first version, but basically the buddybox script ran a find command to create a random playlist of all the music files on the thumbdrive and then started mplayer playing that list (the current version has a separate script for playlist creation). I use cron jobs to start and stop the music.

The music is supplied from my iTunes library (I know it's called Music.app now but I don't care). I have a specific playlist (basically just any song that is rated 4 or 5 stars) for the Buddybox. I run an AppleScript that generates a text file listing all the songs in that playlist, and then use rsync to copy those to a USB thumbdrive.

### Updates New to This Version

The 2026 version adds a few niceties that I've wanted for a while:

I usually use the Buddybox with an old headphone-to-cassette adapter, with the other end in an under-counter clock radio's cassette player. The new version looks for a USB speaker when it starts up. If it finds one, it uses that, otherwise it falls back to headphone jack output. I did this because when I bring home a new pet bird I have to keep it quarantined in a separate room and cage for a month, now I can easily set up a second, identical Buddybox with a USB speaker I have, and everything will work without me needing to adjust any scripts.

The old version would just start playing at whatever volume the cassette player's physical knob was set to. The new version starts at 0% volume and fades in when it starts playing.

The old version required me to SSH in if I wanted to skip a track. I eventually added a shortcut on my iPhone so I could just triple-tap the back. If a song played that I didn't recognize, I'd have to use Shazam. The new one adds a web interface that displays track information and gives me a little control-- I can pause the music, and go to the next or previous track.There are also a couple buttons to aid in playlist management: Even with a few thousand songs on the thumbdrive, I do hear some frequently enough to get tired of them. The "Tired of This" button adds the track info to a text file and skips to the next track. When I update my Buddybox playlist in iTunes I can go through that list and remove songs on it from the playlist. The "Fix Tags" button adds the current track info to a different text file. If I spot an error in a song's displayed metadata, I can log it so I can go back later and fix it in iTunes.

In the old version, if I wanted to add new music I had shut down the Pi, transfer the USB thumbdrive to my Mac, and run a local sync job. That was partly due to the old one running on a Pi 2 with a separate wi-fi dongle that was not great and frequently dropped off the network. The new one is on a Pi 3B and can handle network syncing-- I enabled public key auth for the root user so I can run a sync job over the network. Finding instructions to duplicate that setup is an exercise left for the reader.

### Installation

Make sure you have a root prompt.
Do a git clone or curl the repo to your local machine.
CD into the repo's directory, make sure install.sh is executable, and execute it.

Install.sh will offer to install all available updates, then install the needed components for the scripts: mpv, ffmpeg, socat, bc, and jq
After that it will copy all the scripts to /usr/local/bin, create /var/www/html and copy index.html into it.
Finally, it adds two items to the crontab to launch buddybox and buddyboxUI.py on reboot.

### Usage

Point your browser to `http://[server name or IP]`

![GUI Screenshot](https://git.stango.org/mstango/Buddybox/raw/branch/main/buddyboxUI.png)

The track info area will either show "Not Playing" or the artist, title, album, and album release year.

Just below that it says which track is being played and the count of tracks in the playlist.

Below that are the Prev, Pause, and Next buttons, which I'd hope are self-explanatory. The Pause button will turn into a "Play" button when playback is paused.

Below that are the buttons for playlist management. The text files those buttons create go in /home/administrator.

Below that are two date/timestamps: the time the current playlist was generated, and the last time I ran an rsync job to update the music on the USB drive. The former is auto-generated, the latter is currently set by my manually running `echo $(date +"%B %-d, %Y • %-I:%M %p" | sed "s/am$/AM/;s/pm$/PM/") > /var/www/html/lastsync` when I update the music.

### API Calls 

There is one function not accessible from the GUI, fading in and out.

To fade out the music, use the browser or a curl command with this URL:

`http://[server name or IP]/fade-out?60`

The above example will fade out the music over about a minute (the timing on fades is less than exact in my testing, but close enough for me).

Likewise, to fade in the music, use the browser or a curl command with this URL:

`http://[server name or IP]/fade-in?300`

The above example will wade in the music over about five minutes.