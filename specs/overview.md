# Overview

## Purpose

YouTube Playlist Archiver downloads all videos from every playlist in a YouTube channel. It creates a local archive with per-playlist directories, metadata tracking, and HTML index pages. Designed for incremental updates via cron — only new or previously-failed videos are downloaded on subsequent runs.

## High-Level Flow

```
main()
  └─ PlaylistDownloader.__init__(channel_url, output_dir)
       ├─ Validate YOUTUBE_API_KEY env var
       ├─ Build YouTube Data API v3 client
       ├─ _resolve_channel_id(channel_url)
       └─ _load_global_index()
  └─ run()
       ├─ get_all_playlists()          # paginated API fetch
       └─ for each playlist:
            └─ process_playlist(playlist)
                 ├─ Create playlist directory (sanitized name)
                 ├─ Load or create playlist_metadata.json
                 ├─ get_playlist_videos(playlist_id)
                 ├─ Build position_map from existing metadata
                 ├─ For each video:
                 │    ├─ Determine position (stored > API > conflict → max+1)
                 │    ├─ Skip if already downloaded
                 │    ├─ Record if unavailable (Private/Deleted)
                 │    ├─ Copy from another playlist if in global index
                 │    └─ download_video() with retry
                 ├─ Save metadata after each video
                 └─ generate_html_index()
```

## Data Flow

```
YouTube Data API v3 → playlist/video metadata → yt-dlp download → filesystem
                                ↓                        ↓
                     playlist_metadata.json    global_video_index.json
```

## Output Directory Structure

```
output_dir/
├── global_video_index.json
├── Playlist Title One/
│   ├── playlist_metadata.json
│   ├── index.html
│   ├── 001 - First Video.mp4
│   ├── 001 - First Video.en.vtt
│   ├── 001 - First Video.jpg
│   ├── 002 - Second Video.mp4
│   └── ...
├── Playlist Title Two/
│   ├── playlist_metadata.json
│   ├── index.html
│   └── ...
└── ...
```

## Key Design Patterns

- **Incremental processing**: Videos with `status: "downloaded"` in metadata are skipped on re-run.
- **Deduplication**: Videos appearing in multiple playlists are copied from the first download location via the global index, avoiding redundant downloads.
- **Graceful degradation**: API errors return empty lists; per-playlist exceptions are caught in `run()` so one failure doesn't stop the entire job.
- **Crash safety**: Metadata is saved to disk after every single video, not just at the end.
- **Retry with exponential backoff**: Failed downloads retry up to 3 times with 2s, 4s, 8s delays.
- **Position stability**: Once a video is assigned a position number, it never changes across runs.

## Class Constants

| Constant | Value | Purpose |
|---|---|---|
| `MAX_RETRIES` | `3` | Download retry attempts per video |
| `METADATA_FILE` | `"playlist_metadata.json"` | Per-playlist metadata filename |
| `GLOBAL_INDEX_FILE` | `"global_video_index.json"` | Cross-playlist video index filename |

## Dependencies

| Package | Purpose |
|---|---|
| `yt-dlp` | Video downloading (format selection, subtitles, thumbnails) |
| `google-api-python-client` | YouTube Data API v3 access |

## Source Structure

All logic lives in a single module: `playlist_downloader.py`.
