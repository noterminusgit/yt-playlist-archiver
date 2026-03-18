#!/usr/bin/env python3
"""
YouTube Playlist Archiver

Downloads all videos from all playlists in a YouTube channel/account.
Creates a subdirectory for each playlist and generates an HTML index.
Supports incremental updates for cron jobs.

Usage:
    python playlist_downloader.py <channel_url_or_id> [output_directory]

Example:
    python playlist_downloader.py @username
    python playlist_downloader.py https://www.youtube.com/@username
    python playlist_downloader.py UCxxxxxxxxxxxxxx ./downloads

Requires YOUTUBE_API_KEY environment variable to be set.
"""

import os
import sys
import json
import re
import time
import shutil
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import yt_dlp
import googleapiclient.discovery


logger = logging.getLogger(__name__)


def _configure_logging():
    """Configure logging with file and stream handlers. Called from main() only."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('playlist_downloader.log'),
            logging.StreamHandler()
        ]
    )


class PlaylistDownloader:
    """Manages downloading and archiving YouTube playlists."""

    MAX_RETRIES = 3
    METADATA_FILE = 'playlist_metadata.json'
    GLOBAL_INDEX_FILE = 'global_video_index.json'

    def __init__(self, channel_url: str, output_dir: str = './downloads'):
        """
        Initialize the playlist downloader.

        Args:
            channel_url: YouTube channel URL, handle, or ID
            output_dir: Directory to save downloaded videos
        """
        self.channel_url = channel_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # YouTube Data API setup
        api_key = os.environ.get('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable is required")
        self.youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
        self.channel_id = self._resolve_channel_id(channel_url)

        # Global index to track all downloaded videos and their locations
        self.global_index_path = self.output_dir / self.GLOBAL_INDEX_FILE
        self.global_index = self._load_global_index()

    def _resolve_channel_id(self, channel_url: str) -> str:
        """
        Resolve a channel URL/handle to a channel ID.

        Handles:
            - @username or https://youtube.com/@username
            - UCxxxxxxxx (raw channel ID)
            - https://youtube.com/channel/UCxxxxxxxx

        Returns:
            The UC... channel ID string.
        """
        # Raw channel ID
        if channel_url.startswith('UC') and '/' not in channel_url:
            return channel_url

        # URL with channel ID
        match = re.search(r'/channel/(UC[a-zA-Z0-9_-]+)', channel_url)
        if match:
            return match.group(1)

        # Handle (@username)
        handle_match = re.search(r'@([\w.-]+)', channel_url)
        if handle_match:
            handle = handle_match.group(1)
            response = self.youtube.channels().list(
                part='snippet',
                forHandle=handle
            ).execute()

            if response.get('items'):
                return response['items'][0]['id']
            raise ValueError(f"Could not resolve handle @{handle} to a channel ID")

        raise ValueError(f"Could not parse channel URL: {channel_url}")

    def _load_global_index(self) -> Dict:
        """Load the global video index from disk."""
        if self.global_index_path.exists():
            with open(self.global_index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _save_global_index(self):
        """Save the global video index to disk."""
        with open(self.global_index_path, 'w', encoding='utf-8') as f:
            json.dump(self.global_index, f, indent=2, ensure_ascii=False)

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to be safe for all operating systems.

        Args:
            filename: Original filename

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')

        # Limit length
        if len(filename) > 200:
            filename = filename[:200]

        return filename

    def get_all_playlists(self) -> List[Dict]:
        """
        Fetch all playlists from the channel using YouTube Data API v3.

        Returns:
            List of playlist information dictionaries
        """
        logger.info(f"Fetching playlists for channel: {self.channel_id}")

        playlists = []
        page_token = None

        try:
            while True:
                request = self.youtube.playlists().list(
                    part='snippet',
                    channelId=self.channel_id,
                    maxResults=50,
                    pageToken=page_token
                )
                response = request.execute()

                for item in response.get('items', []):
                    playlists.append({
                        'id': item['id'],
                        'title': item['snippet']['title'],
                        'url': f"https://www.youtube.com/playlist?list={item['id']}"
                    })

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            logger.info(f"Found {len(playlists)} playlists")
            return playlists

        except Exception as e:
            logger.error(f"Error fetching playlists: {e}")
            return []

    def get_playlist_videos(self, playlist_id: str) -> List[Dict]:
        """
        Get all videos from a playlist using YouTube Data API v3.

        Args:
            playlist_id: YouTube playlist ID

        Returns:
            List of video information dictionaries
        """
        logger.info(f"Fetching videos from playlist: {playlist_id}")

        videos = []
        page_token = None

        try:
            while True:
                request = self.youtube.playlistItems().list(
                    part='snippet,status,contentDetails',
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=page_token
                )
                response = request.execute()

                for item in response.get('items', []):
                    video_id = item['snippet']['resourceId']['videoId']
                    title = item['snippet']['title']
                    unavailable = title in ('Private video', 'Deleted video')

                    videos.append({
                        'id': video_id,
                        'title': title,
                        'url': f"https://www.youtube.com/watch?v={video_id}",
                        'playlist_index': item['snippet']['position'],
                        'unavailable': unavailable
                    })

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            logger.info(f"Found {len(videos)} videos in playlist")
            return videos

        except Exception as e:
            logger.error(f"Error fetching playlist videos: {e}")
            return []

    def download_video(self, video_url: str, output_path: Path, video_id: str, position: int) -> Optional[str]:
        """
        Download a single video with retry logic.

        Args:
            video_url: URL of the video
            output_path: Directory to save the video
            video_id: YouTube video ID
            position: 0-based position for filename numbering

        Returns:
            Path to downloaded file if successful, None otherwise
        """
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': str(output_path / f'{position + 1:03d} - %(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'writethumbnail': True,
            'merge_output_format': 'mp4',
        }

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(f"Downloading video {video_id} (attempt {attempt}/{self.MAX_RETRIES})")

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)

                    if info:
                        # Get the actual filename that was created
                        filename = ydl.prepare_filename(info)

                        # Check if file exists
                        if os.path.exists(filename):
                            logger.info(f"Successfully downloaded: {filename}")
                            return filename

                        # Sometimes the extension changes, try to find the file
                        base_name = os.path.splitext(filename)[0]
                        for ext in ['.mp4', '.webm', '.mkv']:
                            potential_file = base_name + ext
                            if os.path.exists(potential_file):
                                logger.info(f"Successfully downloaded: {potential_file}")
                                return potential_file

            except Exception as e:
                logger.warning(f"Attempt {attempt} failed for video {video_id}: {e}")

                if attempt < self.MAX_RETRIES:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to download video {video_id} after {self.MAX_RETRIES} attempts")

        return None

    def copy_video_from_another_playlist(self, video_id: str, target_dir: Path) -> bool:
        """
        Copy a video from another playlist if it exists.

        Args:
            video_id: YouTube video ID
            target_dir: Target directory to copy to

        Returns:
            True if copied successfully, False otherwise
        """
        if video_id not in self.global_index:
            return False

        source_files = self.global_index[video_id].get('files', [])
        if not source_files:
            return False

        # Get the first available source
        source_file = source_files[0]
        source_path = Path(source_file)

        if not source_path.exists():
            logger.warning(f"Source file not found: {source_path}")
            return False

        # Copy the file
        target_path = target_dir / source_path.name

        try:
            shutil.copy2(source_path, target_path)
            logger.info(f"Copied video from {source_path} to {target_path}")

            # Also copy associated files (subtitles, thumbnails)
            base_name = source_path.stem
            for file in source_path.parent.glob(f"{base_name}.*"):
                if file.suffix not in ['.mp4', '.webm', '.mkv']:
                    target_file = target_dir / file.name
                    shutil.copy2(file, target_file)

            return True

        except Exception as e:
            logger.error(f"Error copying video: {e}")
            return False

    def generate_html_index(self, playlist_dir: Path, playlist_title: str, videos: List[Dict]):
        """
        Generate an HTML index page for a playlist.

        Args:
            playlist_dir: Directory containing the playlist videos
            playlist_title: Title of the playlist
            videos: List of video information dictionaries
        """
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{playlist_title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #cc0000;
            padding-bottom: 10px;
        }}
        .info {{
            background-color: #fff;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .video-list {{
            list-style: none;
            padding: 0;
        }}
        .video-item {{
            background-color: #fff;
            margin-bottom: 10px;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
        }}
        .video-number {{
            font-weight: bold;
            color: #cc0000;
            margin-right: 15px;
            min-width: 40px;
        }}
        .video-link {{
            color: #1a73e8;
            text-decoration: none;
            flex-grow: 1;
        }}
        .video-link:hover {{
            text-decoration: underline;
        }}
        .status {{
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            margin-left: 10px;
        }}
        .downloaded {{
            background-color: #d4edda;
            color: #155724;
        }}
        .failed {{
            background-color: #f8d7da;
            color: #721c24;
        }}
    </style>
</head>
<body>
    <h1>{playlist_title}</h1>

    <div class="info">
        <p><strong>Total Videos:</strong> {len(videos)}</p>
        <p><strong>Last Updated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <ol class="video-list">
"""

        for video in videos:
            video_id = video['id']
            title = video['title']
            status = video.get('status', 'unknown')

            status_class = 'downloaded' if status == 'downloaded' else 'failed' if status == 'failed' else ''
            status_text = status.capitalize() if status_class else ''

            html_content += f"""        <li class="video-item">
            <span class="video-number">{video['playlist_index'] + 1}.</span>
            <a href="https://www.youtube.com/watch?v={video_id}" class="video-link" target="_blank">{title}</a>
            {f'<span class="status {status_class}">{status_text}</span>' if status_text else ''}
        </li>
"""

        html_content += """    </ol>
</body>
</html>
"""

        index_path = playlist_dir / 'index.html'
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"Generated HTML index: {index_path}")

    def process_playlist(self, playlist: Dict):
        """
        Process a single playlist: download videos and generate HTML index.

        Args:
            playlist: Playlist information dictionary
        """
        playlist_id = playlist['id']
        playlist_title = playlist['title']
        playlist_url = playlist['url']

        logger.info(f"Processing playlist: {playlist_title}")

        # Create playlist directory
        safe_title = self._sanitize_filename(playlist_title)
        playlist_dir = self.output_dir / safe_title
        playlist_dir.mkdir(parents=True, exist_ok=True)

        # Load or create playlist metadata
        metadata_path = playlist_dir / self.METADATA_FILE
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            metadata = {
                'playlist_id': playlist_id,
                'playlist_title': playlist_title,
                'playlist_url': playlist_url,
                'videos': {}
            }

        # Get all videos from API
        videos = self.get_playlist_videos(playlist_id)

        # Build position map from existing metadata: {position: video_id}
        position_map = {}
        for vid_id, vid_data in metadata['videos'].items():
            if 'position' in vid_data:
                position_map[vid_data['position']] = vid_id

        # Process each video
        for video in videos:
            video_id = video['id']
            video_title = video['title']
            video_url = video['url']
            api_position = video['playlist_index']
            is_unavailable = video.get('unavailable', False)

            # Determine position
            if video_id in metadata['videos'] and 'position' in metadata['videos'][video_id]:
                # Known video - use stored position
                assigned_position = metadata['videos'][video_id]['position']
            else:
                # New video - try API position first
                if api_position not in position_map or position_map.get(api_position) == video_id:
                    assigned_position = api_position
                else:
                    # Conflict - assign next available position
                    assigned_position = max(position_map.keys()) + 1 if position_map else 0
                position_map[assigned_position] = video_id

            video['playlist_index'] = assigned_position

            # Check if already downloaded
            if video_id in metadata['videos']:
                existing_status = metadata['videos'][video_id].get('status')
                if existing_status == 'downloaded':
                    logger.info(f"Video {video_id} already downloaded, skipping")
                    video['status'] = 'downloaded'
                    metadata['videos'][video_id]['position'] = assigned_position
                    continue

            # Handle unavailable videos
            if is_unavailable:
                metadata['videos'][video_id] = {
                    'title': video_title,
                    'url': video_url,
                    'status': 'unavailable',
                    'position': assigned_position
                }
                video['status'] = 'unavailable'
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                continue

            # Check if video exists in another playlist
            if video_id in self.global_index:
                logger.info(f"Video {video_id} found in another playlist, copying...")
                if self.copy_video_from_another_playlist(video_id, playlist_dir):
                    # Update metadata
                    metadata['videos'][video_id] = {
                        'title': video_title,
                        'url': video_url,
                        'status': 'downloaded',
                        'downloaded_at': datetime.now().isoformat(),
                        'copied_from': self.global_index[video_id]['files'][0],
                        'position': assigned_position
                    }
                    video['status'] = 'downloaded'

                    # Update global index
                    video_files = list(playlist_dir.glob(f"*{video_id}*"))
                    if video_files:
                        file_path = str(video_files[0])
                        if file_path not in self.global_index[video_id]['files']:
                            self.global_index[video_id]['files'].append(file_path)

                    # Save metadata
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    self._save_global_index()

                    continue

            # Download the video
            downloaded_file = self.download_video(video_url, playlist_dir, video_id, assigned_position)

            if downloaded_file:
                # Update metadata
                metadata['videos'][video_id] = {
                    'title': video_title,
                    'url': video_url,
                    'status': 'downloaded',
                    'downloaded_at': datetime.now().isoformat(),
                    'file': downloaded_file,
                    'position': assigned_position
                }
                video['status'] = 'downloaded'

                # Update global index
                if video_id not in self.global_index:
                    self.global_index[video_id] = {
                        'title': video_title,
                        'files': []
                    }
                self.global_index[video_id]['files'].append(downloaded_file)

            else:
                # Mark as failed
                metadata['videos'][video_id] = {
                    'title': video_title,
                    'url': video_url,
                    'status': 'failed',
                    'failed_at': datetime.now().isoformat(),
                    'position': assigned_position
                }
                video['status'] = 'failed'

            # Save metadata after each video
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            self._save_global_index()

        # Generate HTML index
        self.generate_html_index(playlist_dir, playlist_title, videos)

        logger.info(f"Finished processing playlist: {playlist_title}")

    def run(self):
        """Run the playlist downloader for all playlists in the channel."""
        logger.info("Starting YouTube Playlist Archiver")

        # Get all playlists
        playlists = self.get_all_playlists()

        if not playlists:
            logger.error("No playlists found. Exiting.")
            return

        # Process each playlist
        for idx, playlist in enumerate(playlists, 1):
            logger.info(f"Processing playlist {idx}/{len(playlists)}")
            try:
                self.process_playlist(playlist)
            except Exception as e:
                logger.error(f"Error processing playlist {playlist.get('title', 'Unknown')}: {e}")
                continue

        logger.info("Finished processing all playlists")


def main():
    """Main entry point for the script."""
    _configure_logging()

    parser = argparse.ArgumentParser(
        description='Download all YouTube playlists from a channel',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s @username
  %(prog)s https://www.youtube.com/@username
  %(prog)s UCxxxxxxxxxxxxxx ./downloads

Requires YOUTUBE_API_KEY environment variable to be set.
        """
    )

    parser.add_argument(
        'channel',
        help='YouTube channel URL or ID (e.g., @username, UCxxxxxx, or full URL)'
    )

    parser.add_argument(
        'output_dir',
        nargs='?',
        default='./downloads',
        help='Output directory for downloaded videos (default: ./downloads)'
    )

    args = parser.parse_args()

    # Initialize and run downloader
    downloader = PlaylistDownloader(args.channel, args.output_dir)
    downloader.run()


if __name__ == '__main__':
    main()
