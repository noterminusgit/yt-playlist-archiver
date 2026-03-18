# Position Management

## Core Rule

**Once a video is assigned a position, that position never changes.** This ensures filenames remain stable across runs.

## Position Assignment Algorithm

For each video returned by the API, position is determined in `process_playlist()`:

```
if video_id exists in metadata with a stored position:
    use stored position                          # ALWAYS wins
else:
    if API position is unoccupied in position_map (or occupied by same video):
        use API position
    else:
        assign max(existing positions) + 1       # conflict resolution
    add to position_map
```

### Position Map

Built at the start of `process_playlist()` from existing metadata:

```python
position_map = {}
for vid_id, vid_data in metadata['videos'].items():
    if 'position' in vid_data:
        position_map[vid_data['position']] = vid_id
```

This maps `{position: video_id}` for all previously-seen videos.

## Scenarios

### First Run (Empty Metadata)

All positions come directly from the API's `snippet.position` (0-based). The position map starts empty, so no conflicts occur.

### Subsequent Runs (Existing Metadata)

- **Already-downloaded video**: Stored position is used. The video's `playlist_index` in the video dict is updated to match the stored position.
- **New video at unoccupied position**: API position is used.
- **New video at occupied position**: Gets `max(position_map.keys()) + 1`.

### Example: Conflict Resolution

```
Metadata has: V1 at position 0, V2 at position 1
API returns:  V1 at 0, V3 at 0 (new video inserted)

Result:
  V1 → position 0 (from metadata)
  V3 → position 2 (max(0,1) + 1, because position 0 is taken by V1)
```

## Gap Preservation

When a video is removed from a playlist, its position number is NOT recycled. The metadata retains the old entry, and existing videos keep their positions. New videos get positions beyond the current maximum.

### Example: Gaps After Deletion

```
Run 1: V1=0, V2=1, V3=2
V2 removed from playlist
Run 2 API returns: V1 at 0, V3 at 1
Result: V1 keeps 0, V3 keeps 2 (from metadata, ignoring API's 1)
Gap at position 1 is preserved in the filesystem.
```

## File Naming

Position is converted to a 1-based, 3-digit zero-padded filename prefix:

```python
f'{position + 1:03d} - %(title)s.%(ext)s'
```

| Internal Position (0-based) | Filename Prefix |
|---|---|
| 0 | `001 - ` |
| 4 | `005 - ` |
| 99 | `100 - ` |

## Unavailable Videos

Private and deleted videos are tracked in metadata with `status: "unavailable"` and their position preserved. No file is created for them, but their position slot is occupied — preventing future videos from claiming it.
