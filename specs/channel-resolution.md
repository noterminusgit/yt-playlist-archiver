# Channel Resolution

## Method

`_resolve_channel_id(channel_url: str) -> str`

Converts a user-provided channel identifier into a canonical `UC...` channel ID string. Called once during `__init__`.

## Supported Input Formats

| Format | Example | Requires API Call |
|---|---|---|
| Raw channel ID | `UCxxxxxxxxxxxxxx` | No |
| Channel URL | `https://www.youtube.com/channel/UCxxxxxxxxxxxxxx` | No |
| Handle URL | `https://www.youtube.com/@username` | Yes |
| Bare handle | `@username` | Yes |

## Resolution Logic

The method checks formats in this order:

### 1. Raw Channel ID (local)
```
if starts with "UC" and contains no "/":
    return as-is
```

### 2. Channel URL (local, regex)
```
regex: /channel/(UC[a-zA-Z0-9_-]+)
if match:
    return captured group
```

### 3. Handle (API call)
```
regex: @([\w.-]+)
if match:
    call youtube.channels().list(part='snippet', forHandle=handle)
    if response has items:
        return items[0]['id']
    else:
        raise ValueError("Could not resolve handle @{handle} to a channel ID")
```

### 4. Nothing matched
```
raise ValueError("Could not parse channel URL: {channel_url}")
```

## API Call Details

For handle resolution only:
- **Endpoint**: `youtube.channels().list`
- **Parameters**: `part='snippet'`, `forHandle=<handle>`
- **Returns**: First item's `id` field

## Error Cases

| Condition | Error |
|---|---|
| Handle not found (API returns empty items) | `ValueError: Could not resolve handle @{handle} to a channel ID` |
| Unrecognized format (no pattern matches) | `ValueError: Could not parse channel URL: {channel_url}` |
| Missing API key | Caught earlier in `__init__` — `ValueError: YOUTUBE_API_KEY environment variable is required` |
