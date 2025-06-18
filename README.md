# YouTube Transcript API

Simple Flask app to extract transcripts from YouTube videos.

## How to use

POST to `/api/transcript` with JSON:
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

Returns the transcript in JSON format.
