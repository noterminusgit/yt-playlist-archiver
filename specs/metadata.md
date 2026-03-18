# Metadata

## Playlist Metadata (`playlist_metadata.json`)

One file per playlist directory. Created on first processing, loaded on subsequent runs.

### Schema

```json
{
  "playlist_id": "PLxxxxxx",
  "playlist_title": "Playlist Title",
  "playlist_url": "https://www.youtube.com/playlist?list=PLxxxxxx",
  "videos": {
    "<video_id>": {
      "title": "Video Title",
      "url": "https://www.youtube.com/watch?v=<video_id>",
      "status": "downloaded | failed | unavailable",
      "position": 0,
      "downloaded_at": "2025-01-01T12:00:00",
      "file": "/path/to/001 - Video Title.mp4",
      "copied_from": "/path/to/source/001 - Video Title.mp4",
      "failed_at": "2025-01-01T12:00:00"
    }
  }
}
```

### Fields by Status

| Field | downloaded | failed | unavailable |
|---|---|---|---|
| `title` | Yes | Yes | Yes |
| `url` | Yes | Yes | Yes |
| `status` | `"downloaded"` | `"failed"` | `"unavailable"` |
| `position` | Yes | Yes | Yes |
| `downloaded_at` | Yes | — | — |
| `file` | Yes (direct download only) | — | — |
| `copied_from` | Yes (copy only) | — | — |
| `failed_at` | — | Yes | — |

## Global Video Index (`global_video_index.json`)

Single file at the root of the output directory. Tracks every successfully downloaded video across all playlists, enabling cross-playlist deduplication.

### Schema

```json
{
  "<video_id>": {
    "title": "Video Title",
    "files": [
      "/absolute/path/to/Playlist One/001 - Video Title.mp4",
      "/absolute/path/to/Playlist Two/003 - Video Title.mp4"
    ]
  }
}
```

The `files` array grows as the same video is copied to additional playlists.

## Video Status Values

| Status | Meaning | Triggers |
|---|---|---|
| `downloaded` | Video file exists on disk | Successful `download_video()` or `copy_video_from_another_playlist()` |
| `failed` | Download attempted but failed after all retries | `download_video()` returned `None` |
| `unavailable` | Video is private or deleted | Title is exactly `"Private video"` or `"Deleted video"` |

## Persistence Strategy

- **Save frequency**: After every single video processed (not batched per playlist).
- **Crash safety**: At most one video's state is lost on crash.
- **Save operations**: Both `playlist_metadata.json` and `global_video_index.json` are written after download/copy. Only `playlist_metadata.json` is written for unavailable videos (no global index update needed).
- **Encoding**: UTF-8 with `ensure_ascii=False` — preserves non-ASCII characters in titles.
- **Format**: Pretty-printed with `indent=2`.

## Load/Save Methods

| Method | File | Behavior |
|---|---|---|
| `_load_global_index()` | `global_video_index.json` | Returns `{}` if file doesn't exist |
| `_save_global_index()` | `global_video_index.json` | Overwrites entire file |

Playlist metadata is loaded/saved inline within `process_playlist()` using direct `json.load()`/`json.dump()` calls.
