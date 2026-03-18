# Download Pipeline

## download_video()

Downloads a single video using yt-dlp with retry logic.

**Signature**: `download_video(video_url, output_path, video_id, position) -> Optional[str]`

### yt-dlp Configuration

```python
{
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'outtmpl': '{output_path}/{position+1:03d} - %(title)s.%(ext)s',
    'quiet': False,
    'no_warnings': False,
    'ignoreerrors': False,
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['en'],
    'writethumbnail': True,
    'merge_output_format': 'mp4',
}
```

**Format priority**: MP4 video + M4A audio → MP4 single file → best available.

**Output template**: `{position+1:03d} - %(title)s.%(ext)s` — 1-based zero-padded position prefix.

### Retry Logic

- **Max attempts**: 3 (`MAX_RETRIES`)
- **Backoff**: Exponential — `2^attempt` seconds
  - After attempt 1: sleep 2s
  - After attempt 2: sleep 4s
  - After attempt 3: no sleep (final failure)
- On success at any attempt, returns immediately.
- Returns `None` after all retries exhausted.

### File Discovery

After `yt_dlp.extract_info()` succeeds:

1. Get prepared filename via `ydl.prepare_filename(info)`
2. Check if that exact file exists → return it
3. If not, try alternate extensions in order: `.mp4`, `.webm`, `.mkv`
4. If no file found at any extension, the attempt is treated as if `info` was None (loops to next retry or returns `None`)

### Return Value

- **Success**: Absolute file path string
- **Failure**: `None`

## copy_video_from_another_playlist()

Deduplicates downloads by copying a video already present in another playlist.

**Signature**: `copy_video_from_another_playlist(video_id, target_dir) -> bool`

### Logic

1. Check `global_index[video_id]` exists → `False` if not
2. Check `files` list is non-empty → `False` if empty
3. Check first source file exists on disk → `False` if missing
4. Copy main video file via `shutil.copy2` (preserves metadata)
5. Copy associated files (same stem, different extension) — **excluding** video extensions (`.mp4`, `.webm`, `.mkv`)
6. Return `True`

**Associated files copied**: Subtitles (`.en.vtt`, etc.), thumbnails (`.jpg`, `.webp`), etc.

**Associated files skipped**: Other video format files to avoid duplication.

**Error handling**: Any exception during copy → logs error, returns `False`.

## process_playlist() Orchestration

The per-video decision tree within `process_playlist()`:

```
for each video from API:
    1. Determine position (see position-management.md)
    2. If video_id in metadata with status "downloaded":
         → skip (log "already downloaded")
    3. If video is unavailable (Private/Deleted):
         → save metadata with status "unavailable", continue
    4. If video_id in global_index:
         → copy_video_from_another_playlist()
         → if success: save metadata with status "downloaded" + copied_from
    5. Otherwise:
         → download_video()
         → if success: save metadata with status "downloaded", update global index
         → if failure: save metadata with status "failed"
    6. Save metadata and global index to disk

After all videos:
    generate_html_index()
```

### Metadata Persistence

`playlist_metadata.json` and `global_video_index.json` are both saved after **every video** — not batched. This means a crash mid-playlist loses at most one video's progress.

## run() Error Handling

```python
for playlist in playlists:
    try:
        self.process_playlist(playlist)
    except Exception:
        logger.error(...)
        continue  # next playlist
```

A failure in one playlist does not stop processing of remaining playlists.
