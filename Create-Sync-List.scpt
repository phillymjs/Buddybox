(*

NOTE1: This script requires swiftDialog (https://github.com/swiftDialog/swiftDialog) for the progress dialog.
NOTE2: To use the sync command below, the Raspberry Pi serving as your Buddybox must have root login enabled, ideally only via preauthorized key.
SYNC COMMAND TO USE THE OUTPUT FILE (update paths/addresses as required):

rsync -avz --progress --prune-empty-dirs \
  --no-owner --no-group --no-perms \
  --delete --delete-excluded \
  --filter=". /Users/username/path/to/synclist.txt" \
  "/Users/username/Music/Apple Music/Media.localized/Music/" \
  root@buddyboxaddress:/mnt/music/ && ssh root@buddyboxaddress 'touch /mnt/music/.lastsync'
 
Add a line with "+ .track" line below the "+ playlist" line if you do NOT want the playlist regenerated after a sync.
*)

tell application "Music"
	set targetFileList to "/Users/username/path/to/synclist.txt"
	set musicDirectory to "/Users/username/Music/Apple Music/Media.localized/Music"
	set targetPlaylist to "Buddybox"
	
	-- Delete the synclist file if it's present
	try
		tell application "System Events"
			if exists file targetFileList then
				delete file targetFileList
			end if
		end tell
	end try
	
	-- Start building a new synclist file
	set myFile to open for access (targetFileList) with write permission
	write "+ */
+ playlist
" to myFile starting at eof as «class utf8»
	set trackCount to count of tracks of playlist targetPlaylist
	do shell script "/usr/local/bin/dialog --ontop --title \"\" --message \"Exporting Playlist to Sync File: " & trackCount & " Items\" --mini --icon \"/System/Applications/Music.app\" --progress \"reset\" --commandfile \"/var/tmp/dialog.log\" > /dev/null 2>&1 &"
	delay 1
	repeat with currentTrack from 1 to trackCount
		set percentage to (currentTrack * 100) div trackCount
		do shell script "echo \"progress: " & percentage & "\" >> /var/tmp/dialog.log"
		set theFile to (location of file track currentTrack of playlist targetPlaylist)
		set theFilePOSIX to POSIX path of theFile
		set theFilePOSIX to "+ " & (characters ((count of characters of musicDirectory) + 1) through (count of characters of theFilePOSIX) of theFilePOSIX) as string
		write theFilePOSIX & "
" to myFile starting at eof as «class utf8»
	end repeat
	write "- *
" to myFile starting at eof as «class utf8»
	close access myFile
	beep
	do shell script "echo \"message: \"Synclist Creation Complete!\"\" >> /var/tmp/dialog.log"
	delay 5
	do shell script "echo \"quit:\" >> /var/tmp/dialog.log"
end tell
