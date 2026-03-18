# CLI Interface

## Entry Point

`main()` in `playlist_downloader.py`, invoked via:

```bash
python playlist_downloader.py <channel> [output_dir]
```

Or via `if __name__ == '__main__': main()`.

## Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `channel` | Yes | — | YouTube channel URL, handle, or ID |
| `output_dir` | No | `./downloads` | Directory for downloaded videos |

### Accepted Channel Formats

- `@username` — bare handle
- `https://www.youtube.com/@username` — handle URL
- `UCxxxxxxxxxxxxxx` — raw channel ID
- `https://www.youtube.com/channel/UCxxxxxxxxxxxxxx` — channel URL

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `YOUTUBE_API_KEY` | Yes | Google API key with YouTube Data API v3 enabled |

Missing `YOUTUBE_API_KEY` raises `ValueError` during `PlaylistDownloader.__init__()`.

## Logging Configuration

`_configure_logging()` is called at the start of `main()`:

- **Level**: `INFO`
- **Format**: `%(asctime)s - %(levelname)s - %(message)s`
- **Handlers**:
  - `FileHandler('playlist_downloader.log')` — writes to working directory
  - `StreamHandler()` — writes to stderr

Logging is configured via `logging.basicConfig()`, so it only runs once. The `logger` module-level variable uses `logging.getLogger(__name__)`.

## Execution Flow

```
main()
├─ _configure_logging()
├─ argparse.ArgumentParser.parse_args()
├─ PlaylistDownloader(args.channel, args.output_dir)
└─ downloader.run()
```

## Exit Conditions

| Condition | Behavior |
|---|---|
| Missing `channel` argument | `argparse` raises `SystemExit` (exit code 2) |
| Missing `YOUTUBE_API_KEY` | `ValueError` raised |
| No playlists found | `run()` logs error and returns (exit code 0) |
| Per-playlist errors | Logged and skipped, processing continues |

## Usage Examples

```bash
# Archive by handle
export YOUTUBE_API_KEY="your-api-key"
python playlist_downloader.py @username

# Archive by URL with custom output directory
python playlist_downloader.py https://www.youtube.com/@username ./my-archive

# Archive by channel ID
python playlist_downloader.py UCxxxxxxxxxxxxxx /data/youtube-archive
```

## argparse Help Text

```
usage: playlist_downloader.py [-h] channel [output_dir]

Download all YouTube playlists from a channel

positional arguments:
  channel     YouTube channel URL or ID (e.g., @username, UCxxxxxx, or full URL)
  output_dir  Output directory for downloaded videos (default: ./downloads)

Examples:
  playlist_downloader.py @username
  playlist_downloader.py https://www.youtube.com/@username
  playlist_downloader.py UCxxxxxxxxxxxxxx ./downloads

Requires YOUTUBE_API_KEY environment variable to be set.
```
