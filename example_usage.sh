#!/bin/bash
# Example usage script for YouTube Playlist Archiver

# Install dependencies (run this once)
# pip install -r requirements.txt

# Example 1: Download all playlists from a channel using @username
# python playlist_downloader.py @username

# Example 2: Download all playlists from a channel using full URL
# python playlist_downloader.py https://www.youtube.com/@username

# Example 3: Download to a custom directory
# python playlist_downloader.py @username /path/to/downloads

# Example 4: Download using channel ID
# python playlist_downloader.py UCxxxxxxxxxxxxxx

# For cron job, add to crontab:
# 0 2 * * * cd /path/to/yt-playlist-archiver && /usr/bin/python3 playlist_downloader.py @username /path/to/downloads >> /path/to/logs/archiver.log 2>&1
