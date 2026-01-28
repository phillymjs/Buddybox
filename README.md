# Buddybox

Much-improved version of a Raspberry Pi-based music player I first created in 2017.

### Table of Contents

[Background](#background)

[Installation](#installation)

[Usage](#usage)

[API Calls](#api-calls)

[Music Syncing Process](#music-syncing-process)

[Future Plans](#future-plans)

---

### Background

I used to keep a radio playing to keep my pet birds company when I wasn't in the room with them or not at home. During the time I spent in the room, I got sick of hearing the same handful of songs over and over, and the ads were constant and obnoxious. I set out to make a simple music player that was completely self-contained, that needed no network access, that would start up and automatically play a large selection of only songs I really liked, and that would do so for as long as it had power. Since I thought of it as a jukebox and the bird I had at the time was named Buddy, I called it the Buddybox. The included icons feature a photo of him.

Why not just use a portable MP3 player? I had a very specific set of requirements in mind, and I couldn't guarantee some cheap piece of crap from Amazon would meet all of them. It also served as a "boredom project"-- I wanted to pass the time doing something productive during a Christmas week at the office, when everyone else was off and it was dead. Since I had randomly been given a free Raspberry Pi B+ around that time, I built the original Buddybox with it-- it has now been retired and replaced with a 3B+ for this new incarnation.

The music is supplied from my iTunes library (I know it's called Music.app now but I don't care). I have a specific playlist (basically just any song that is rated 4 or 5 stars) for the Buddybox. I run an AppleScript (included in the repo) that generates a text file listing all the songs in that playlist, and then use a manual rsync command to copy those to a USB thumbdrive.


### Features New to This Version

In the original version, the buddybox script simply ran a find command to create a random playlist of all the music files on the thumbdrive and then started mplayer playing that list on endless loop. There was no UI to speak of, I needed to SSH in to skip tracks. It was set to reboot daily, and regenerated the playlist on reboot, so some songs were played frequently enough that I noticed. To add new music, I had to shut the Pi down and transfer the thumbdrive to my Mac. I addressed those shortcomings and made additional improvements:

- **Based on mpv:** Some features I wanted to add to the project required features not present in mplayer.
- **Web UI:** Track info display and playback control (Play/Pause/Skip) via browser.
- **Smart Audio:** Automatically detects a connected USB speaker, falls back to the 3.5mm jack if one isn't found. (Some tweaking may be required for your specific USB speaker).
- **More Music Variety:** Keeps track of where it is in the playlist and starts up from that song if rebooted.
- **Soft Start:** Music fades in gracefully rather than starting at full volume.
- **Playlist Management:** Dedicated "Tired of This" and "Fix Tags" buttons to help me curate my library.
- **Network Sync:** Supports rsync over SSH (via passwordless root login) for easy music updates.

### Installation

- Make sure you have a root prompt.
- Do a git clone or curl the repo to your Raspberry Pi.
- Plug in a USB thumbdrive (preferably ExFAT-formatted) with music files on it.
- CD into the repo's directory, make sure install.sh is executable, and execute it.

Install.sh will offer to install all available updates, then install the needed components for the scripts: mpv, ffmpeg, socat, bc, and jq

Next, it will copy all the scripts to /usr/local/bin, and copy index.html, manifest.json, and the icons folder into /var/www/html, creating it first if needed.

Finally, it adds three items to the crontab that will run on boot: one clears the log file and makes an entry in it noting boot time, the other two launch buddybox and buddyboxUI.py.

Settings are stored in the **.env** file. (Currently only used by the Bash portion of the project, but eventually the Python portion will also take settings from there.)

### Usage

Point your browser to `http://[address]`, and you should see this:

<div align="center">
  <img src="https://git.stango.org/mstango/Buddybox/raw/branch/main/buddyboxUI.png" alt="GUI Screenshot" width="450">
</div>

If mpv is running, the track info area will show the artist, title, album, and album release year, otherwise "Not Playing" is displayed.

Just below that it shows the current track number and the count of tracks in the playlist.

Below that are the Prev, Pause, and Next buttons, providing standard playback control. The Pause button will turn into a "Play" button when playback is paused. If playback is [locked out](#lockout), the Play button will be disabled and display a red padlock icon. In a desktop browser, the spacebar will toggle play/pause and the left and right arrow keys control next/previous track.

Below that are the buttons for playlist management. The text files those buttons write to currently go in /home/administrator-- if you use a different default account on the Pi, you'll obviously have to change that.

Below that are two date/timestamps: the time the current playlist was generated, and the last time an rsync job was run to update the music on the USB thumbdrive. The former is auto-generated, the latter is currently set by my manually running `touch` on a file named **.lastsync** located in the music directory.

### API Calls
#### These functions are also accessible via the web UI:

To toggle playback:

`http://[address]/pause`

To move to the previous track or the next track:

`http://[address]/prev` or `http://[address]/next`

To add the current track to the "Sick of This" list (and automatically skip to the next track):

`http://[address]/sick`

To add the current track to the "Fix Tags" list:

`http://[address]/fix`

#### These functions are only accessible via API:

To fade out the music:

`http://[address]/fade-out?60`

The above example will fade out the music over one minute.

**Note that pressing the Play button in the UI or sending a "pause" API command after a fade-out will resume the playback immediately at the pre-fade-out volume level.**

Likewise, to fade in the music:

`http://[address]/fade-in?300`

The above example will fade in the music over five minutes.

<a name="lockout" style="cursor: default; color: black; text-decoration:none;">To lock out or unlock playback:</a>

`http://[address]/lock` or `http://[address]/unlock`

Locking out playback prevents accidental starting of the player. I use this by having Home Assistant send a fade-out API command and then a lock API command when I go to bed at night, and the reverse when I wake up in the morning. If mpv restarts or the Pi reboots while lockout is enabled, e.g. due to a power outage, it will not automatically start playing. You can also lock out the ability to pause while music is playing. I'm not sure of the utility of that, but I didn't see a need to prevent it.

### Music Syncing Process

Just a few notes: First off, there's no requirement to use the Applescript, you can just manually throw MP3 and/or M4A files onto a USB thumbdrive if you prefer. I had a lot of music and I wanted the files to be organized like they are in my iTunes library, so the script made sense for me.

The Applescript has a few hard-coded variables that will need to be updated for your machine. Check the comments in the script file for more details.

Before running a sync, it's best to stop playback. The rsync command will remove the file that holds the currently-playing track, which will cause a new playlist to be created when you resume playback after a sync. The exact rsync command is in comments in the Applescript file. I will eventually make this into more of a turn-key applet with an actual GUI.

### Future Plans

Generate a new playlist when the end of the current playlist is reached, and begin playing it once the last song on the old playlist finished playing. This may require breaking out creation of the playlist into a separate script. This is far from a priority, since if I just loop my current 2,800+ song playlist I have almost 8 days of music before a song will be repeated.

Move whatever functionality I can into the Python script. I'm still a relative Python n00b, but I know bash like the back of my hand, so I stuck to what I knew in the interest of getting it up and running. I also leaned quite a bit on Gemini for the Python bits, but I reviewed its source and made my own adjustments. I learned more than one language by reading source code I didn't write and changing stuff to see what happened, so I expect Python will be somewhat the same.

Improvements to the Applescript that creates the sync list. I'd like to give it a GUI to ask the user to pick a playlist at least on the initial run, and have it ask to run the sync automatically after the list is generated.
