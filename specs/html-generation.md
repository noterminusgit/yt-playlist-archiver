# HTML Generation

## Method

`generate_html_index(playlist_dir, playlist_title, videos)`

Called once at the end of `process_playlist()`, after all videos are processed. Writes `index.html` to the playlist directory.

## Output File

`{playlist_dir}/index.html` — a self-contained HTML page with inline CSS, no external dependencies.

## HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{playlist_title}</title>
    <style>/* inline CSS */</style>
</head>
<body>
    <h1>{playlist_title}</h1>
    <div class="info">
        <p>Total Videos: {count}</p>
        <p>Last Updated: {timestamp}</p>
    </div>
    <ol class="video-list">
        <!-- one <li> per video -->
    </ol>
</body>
</html>
```

## Info Box

| Field | Value |
|---|---|
| Total Videos | `len(videos)` — count of all videos passed in, regardless of status |
| Last Updated | `datetime.now().strftime('%Y-%m-%d %H:%M:%S')` — local time at generation |

## Video List Rendering

Each video is rendered as a list item:

```html
<li class="video-item">
    <span class="video-number">{position + 1}.</span>
    <a href="https://www.youtube.com/watch?v={video_id}" class="video-link" target="_blank">{title}</a>
    <span class="status {status_class}">{status_text}</span>  <!-- if applicable -->
</li>
```

### Numbering

Uses `video['playlist_index'] + 1` — 1-based display, derived from the (possibly reassigned) 0-based position.

### Status Badges

| Status Value | CSS Class | Display Text | Shown? |
|---|---|---|---|
| `"downloaded"` | `downloaded` | `Downloaded` | Yes |
| `"failed"` | `failed` | `Failed` | Yes |
| `"unknown"` or absent | — | — | No badge rendered |

Note: `"unavailable"` status does not get a dedicated badge — it falls through to the "no badge" case since it has no matching CSS class.

## Inline CSS

The page uses a responsive layout:
- **Body**: `max-width: 1200px`, centered, light gray background (`#f5f5f5`)
- **Header**: Red underline (`#cc0000`)
- **Info box**: White card with shadow
- **Video items**: White cards, flexbox layout with number + link + optional status badge
- **Status badges**: Green background for downloaded (`#d4edda`), red background for failed (`#f8d7da`)
- **Links**: Blue (`#1a73e8`), open in new tab (`target="_blank"`)
