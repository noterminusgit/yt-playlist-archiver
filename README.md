# YouTube Playlist Archiver

A Python script to download and archive all videos from all playlists in a YouTube channel or account. Perfect for creating local backups of educational content, favorite playlists, or entire channels.

## Features

- Downloads all videos from all playlists in a YouTube channel
- Creates separate subdirectories for each playlist
- Generates an HTML index page for each playlist showing videos in order
- Supports incremental updates (only downloads new content)
- Retry logic with exponential backoff (max 3 attempts per video)
- Copies videos that appear in multiple playlists instead of re-downloading
- Cron-friendly for automated archiving
- Tracks download status and metadata for each playlist
- Downloads subtitles and thumbnails when available

## Requirements

- Python 3.7 or higher
- yt-dlp library

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/yt-playlist-archiver.git
cd yt-playlist-archiver
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Download all playlists from a channel to the default `./downloads` directory:

```bash
python playlist_downloader.py @username
```

or

```bash
python playlist_downloader.py https://www.youtube.com/@username
```

### Custom Output Directory

Specify a custom output directory:

```bash
python playlist_downloader.py @username /path/to/downloads
```

### Channel ID Format

You can also use the channel ID directly:

```bash
python playlist_downloader.py UCxxxxxxxxxxxxxx
```

## How It Works

1. **Fetches all playlists** from the specified channel
2. **Creates subdirectories** for each playlist (sanitized names)
3. **Downloads videos** in each playlist with:
   - Up to 3 retry attempts with exponential backoff
   - Best quality MP4 format
   - Subtitles (if available)
   - Thumbnails
4. **Tracks progress** using JSON metadata files:
   - `playlist_metadata.json` in each playlist folder
   - `global_video_index.json` in the root output directory
5. **Generates HTML index** for each playlist showing:
   - Video titles in playlist order
   - Download status
   - Links to YouTube videos
   - Last update timestamp
6. **Handles duplicates** by copying videos that appear in multiple playlists

## Incremental Updates

The script is designed to be run multiple times (e.g., via cron) without re-downloading existing content:

- Videos already downloaded are skipped
- Only new videos are downloaded
- Missing content is NOT removed (append-only)
- Failed downloads are retried on subsequent runs

### Cron Job Example

To run the archiver daily at 2 AM:

```bash
0 2 * * * cd /path/to/yt-playlist-archiver && /usr/bin/python3 playlist_downloader.py @username /path/to/downloads >> /path/to/logs/archiver.log 2>&1
```

## Output Structure

```
downloads/
├── global_video_index.json           # Global index of all downloaded videos
├── Playlist Name 1/
│   ├── playlist_metadata.json        # Playlist-specific metadata
│   ├── index.html                    # HTML index of videos in this playlist
│   ├── Video Title 1.mp4
│   ├── Video Title 1.en.vtt          # Subtitles (if available)
│   ├── Video Title 1.jpg             # Thumbnail
│   └── Video Title 2.mp4
├── Playlist Name 2/
│   ├── playlist_metadata.json
│   ├── index.html
│   └── ...
└── playlist_downloader.log           # Log file
```

## Metadata Files

### global_video_index.json

Tracks all downloaded videos across all playlists:

```json
{
  "video_id_here": {
    "title": "Video Title",
    "files": [
      "/path/to/downloads/Playlist 1/Video Title.mp4",
      "/path/to/downloads/Playlist 2/Video Title.mp4"
    ]
  }
}
```

### playlist_metadata.json

Tracks videos in each playlist:

```json
{
  "playlist_id": "PLxxxxxxxxxxxxxx",
  "playlist_title": "Playlist Name",
  "playlist_url": "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxx",
  "videos": {
    "video_id_here": {
      "title": "Video Title",
      "url": "https://www.youtube.com/watch?v=xxxxxxxxxxx",
      "status": "downloaded",
      "downloaded_at": "2025-01-07T10:30:00",
      "file": "/path/to/Video Title.mp4"
    }
  }
}
```

## Logging

The script logs all activities to:
- Console (stdout)
- `playlist_downloader.log` file in the output directory

Log levels:
- INFO: Normal operations
- WARNING: Retries and minor issues
- ERROR: Failed downloads and critical errors

## Rate Limiting Protection

The script includes several features to avoid hitting YouTube's rate limits:

1. **Retry logic**: Max 3 attempts per video with exponential backoff (2s, 4s, 8s)
2. **Incremental updates**: Skips already-downloaded videos
3. **Graceful failure**: Continues with next video after max retries

## Troubleshooting

### No playlists found

- Verify the channel URL or ID is correct
- Some channels may not have public playlists
- Try using the channel ID (UCxxxxxxxxxxxxxx) format

### Download failures

- Check your internet connection
- Verify the videos are publicly accessible
- Some videos may be geo-restricted or age-restricted
- Update yt-dlp: `pip install --upgrade yt-dlp`

### Permission errors

- Ensure you have write permissions in the output directory
- On Windows, avoid special characters in paths

## Advanced Usage

### Updating yt-dlp

Keep yt-dlp up to date for best compatibility:

```bash
pip install --upgrade yt-dlp
```

### Custom yt-dlp Options

Edit the `ydl_opts` dictionary in `playlist_downloader.py` to customize download options:

```python
ydl_opts = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': str(output_path / '%(title)s.%(ext)s'),
    # Add more options here
}
```

See [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp#usage-and-options) for all available options.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for personal archival purposes only. Respect copyright laws and YouTube's Terms of Service. Only download content you have the right to download.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
