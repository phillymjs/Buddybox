# Buddybox

Much-improved version of a Raspberry Pi-based music player I first created in 2017.

### Background

I used to keep a radio playing to keep my pet birds company when I wasn't in the room with them or not at home. Over time, I got sick of constantly hearing the same handful of songs, and the ads were constant and obnoxious. I set out to make a simple music player that was completely self-contained, that needed no network access, that would start up and automatically play only the music I liked, and that would do it for as long as it had power. Since I thought of it as a jukebox, the bird I had at the time was named Buddy, and I was building it for his benefit, I called it the Buddybox.

Why not just use a portable MP3 player? I had a very specific set of requirements in mind, and I couldn't guarantee some cheap piece of crap from Amazon would meet all of them. It also served as a holiday 'boredom project' to pass the time doing something productive during a slow week at the office. Since I had randomly been given a free Raspberry Pi B+ around that time, I built the original Buddybox with it-- it has now been retired and replaced with a 3B+ for this new incarnation.

The music is supplied from my iTunes library (I know it's called Music.app now but I don't care). I have a specific playlist (basically just any song that is rated 4 or 5 stars) for the Buddybox. I run an AppleScript that generates a text file listing all the songs in that playlist, and then use rsync to copy those to a USB thumbdrive.

In the original version, the buddybox script simply ran a find command to create a random playlist of all the music files on the thumbdrive and then started mplayer playing that list on endless loop. I needed to SSH in to skip tracks, and had to shut the Pi down and transfer the thumbdrive to my Mac to add new music.

### Features New to This Version
- **Based on mpv:** Some features I wanted to add to the Buddybox required features not present in mplayer.
- **Web UI:** Track info display and playback control (Play/Pause/Skip) via browser.
- **Smart Audio:** Automatically detects a connected USB speaker, falls back to the 3.5mm jack if one isn't found. (Some tweaking may be required for your specific USB speaker).
- **Soft Start:** Music fades in gracefully rather than jarringly starting at full volume.
- **Playlist Management:** Dedicated "Tired of This" and "Fix Tags" buttons to help me curate my library.
- **Network Sync:** Supports rsync over SSH (via passwordless root login) for easy music updates.

### Installation

- Make sure you have a root prompt.
- Do a git clone or curl the repo to your local machine.
- CD into the repo's directory, make sure install.sh is executable, and execute it.

Install.sh will offer to install all available updates, then install the needed components for the scripts: mpv, ffmpeg, socat, bc, and jq

After that it will copy all the scripts to /usr/local/bin, create /var/www/html and copy index.html into it.

Finally, it adds two items to the crontab to launch buddybox and buddyboxUI.py on reboot.

### Usage

Point your browser to `http://[address]`, and you should see this:

<div align="center">
  <img src="https://git.stango.org/mstango/Buddybox/raw/branch/main/buddyboxUI.png" alt="GUI Screenshot" width="450">
</div>

If mpv is running, the track info area will show the artist, title, album, and album release year, otherwise "Not Playing" is displayed.

Just below that it shows the current track number and the count of tracks in the playlist.

Below that are the Prev, Pause, and Next buttons, providing standard playback control. The Pause button will turn into a "Play" button when playback is paused, as it was when the above screenshot was taken. When playback is locked out, the button will say so and display a red padlock icon.

Below that are the buttons for playlist management. The text files those buttons create go in /home/administrator-- if you use a different default account on the Pi, you'll obviously have to change that.

Below that are two date/timestamps: the time the current playlist was generated, and the last time an rsync job was run to update the music on the USB thumbdrive. The former is auto-generated, the latter is currently set by my manually running `touch` on a file named **.lastsync** located in the music directory.

### API Calls
#### These functions are also accessible via the web UI:

To toggle playback:

`http://[address]/pause`

To move to the previous track or the next track:

`http://[address]/prev` or `http://[address]/next`

To add the current track to the "Sick of This" list:

`http://[address]/sick`

To add the current track to the "Fix Tags" list:

`http://[address]/fix`

#### These functions are only accessible via API:

To fade out the music:

`http://[address]/fade-out?60`

The above example will fade out the music over about a minute (the timing on fades is less than exact in my testing, but close enough for me). **Note that pressing the Play button in the UI or sending a "pause" API command after a fade-out will resume the playback immediately at the pre-fade-out volume level.**

Likewise, to fade in the music:

`http://[address]/fade-in?300`

The above example will fade in the music over about five minutes.

To lock out or unlock playback:

`http://[address]/lock` or `http://[address]/unlock`

Locking out playback prevents accidental starting of the player. I use this by having Home Assistant send a fade-out command and then a lock command when I go to bed at night, and the reverse when I wake up in the morning. If mpv restarts or the Pi reboots while lockout is enabled, e.g. due to a power outage, it will not automatically start playing.

### Future Plans

Generate a new playlist when the end of the current playlist is reached, and begin playing it once the last song on the old playlist finished playing. This may require breaking out creation of the playlist into a separate script.

I'd like to move whatever I can into the Python script. I'm still a relative Python n00b, but I know bash like the back of my hand, so I stuck to what I knew in the interest of getting it up and running. I also leaned quite a bit on Gemini for the Python bits, but I reviewed its source and made my own adjustments. I learned more than one language by reading source code I didn't write and changing stuff to see what happened, so I expect Python will be somewhat the same.