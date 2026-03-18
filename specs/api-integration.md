# API Integration

## Setup

The YouTube Data API v3 client is built during `__init__`:

```python
api_key = os.environ.get('YOUTUBE_API_KEY')
self.youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=api_key)
```

A missing `YOUTUBE_API_KEY` raises `ValueError` before any API calls are made.

## get_all_playlists()

Fetches every playlist belonging to the resolved channel.

**Endpoint**: `youtube.playlists().list`

**Parameters**:
| Parameter | Value |
|---|---|
| `part` | `'snippet'` |
| `channelId` | `self.channel_id` |
| `maxResults` | `50` |
| `pageToken` | Next page token (initially `None`) |

**Pagination**: Follows `nextPageToken` until absent.

**Return schema** (list of dicts):
```json
[
  {
    "id": "PLxxxxxx",
    "title": "Playlist Title",
    "url": "https://www.youtube.com/playlist?list=PLxxxxxx"
  }
]
```

**Error handling**: Any exception → logs error, returns `[]`.

## get_playlist_videos()

Fetches every video in a single playlist.

**Endpoint**: `youtube.playlistItems().list`

**Parameters**:
| Parameter | Value |
|---|---|
| `part` | `'snippet,status,contentDetails'` |
| `playlistId` | Playlist ID |
| `maxResults` | `50` |
| `pageToken` | Next page token (initially `None`) |

**Pagination**: Follows `nextPageToken` until absent.

**Unavailability detection**: A video is marked `unavailable: True` if its `snippet.title` is exactly `"Private video"` or `"Deleted video"`. These are sentinel titles returned by the API for inaccessible videos.

**Return schema** (list of dicts):
```json
[
  {
    "id": "video_id",
    "title": "Video Title",
    "url": "https://www.youtube.com/watch?v=video_id",
    "playlist_index": 0,
    "unavailable": false
  }
]
```

The `playlist_index` comes from `item['snippet']['position']` (0-based).

**Error handling**: Any exception → logs error, returns `[]`.

## Quota Considerations

- `playlists.list` costs 1 unit per call (50 results per page).
- `playlistItems.list` costs 1 unit per call (50 results per page).
- Default daily quota is 10,000 units.
- A channel with 10 playlists averaging 100 videos each ≈ 10 + 20 = 30 quota units per full run.
- The `channels.list` call for handle resolution costs 1 unit (one-time per run).
