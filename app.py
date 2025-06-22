import os
import re
from flask_cors import CORS
from flask import Flask, request
from flask_restx import Api, Resource, fields
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

app = Flask(__name__)
CORS(app)
api = Api(app,
          version="1.0",
          title="YouTube Transcript API",
          description="Get transcripts from YouTube videos",
          doc="/api/docs",
          prefix="/api")

ns = api.namespace("transcript", description="Transcript operations")

transcript_segment = api.model("TranscriptSegment", {
    "start": fields.Float,
    "duration": fields.Float,
    "text": fields.String
})

transcript_response = api.model("TranscriptResponse", {
    "status": fields.String,
    "video_id": fields.String,
    "video_url": fields.String,
    "thumbnail_url": fields.String,  # NEW FIELD
    "transcript": fields.List(fields.Nested(transcript_segment)),
    "transcript_type": fields.String,
    "language": fields.String,
    "language_code": fields.String,
    "total_segments": fields.Integer
})

def extract_video_id(url):
    patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&\n?#]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^&\n?#]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([^&\n?#]+)',
        r'(?:https?://)?youtu\.be/([^&\n?#]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([^&\n?#]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@ns.route("")
class TranscriptAPI(Resource):
    @ns.doc(params={"url": "YouTube video URL"})
    @ns.marshal_with(transcript_response)
    def get(self):
        """Get transcript via YouTube URL (GET)"""
        url = request.args.get('url', '').strip()
        video_id = extract_video_id(url)

        if not url or not video_id:
            api.abort(400, "Missing or invalid YouTube URL")

        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = None

            try:
                transcript = transcript_list.find_transcript(['en'])
            except NoTranscriptFound:
                for t in transcript_list:
                    if not t.is_generated:
                        transcript = t
                        break
                if not transcript:
                    for t in transcript_list:
                        if t.is_generated:
                            transcript = t
                            break

            if not transcript:
                api.abort(404, "No transcripts found")

            transcript_data = transcript.fetch()
            formatted = [{
                'start': getattr(entry, 'start', 0.0),
                'duration': getattr(entry, 'duration', 0.0),
                'text': getattr(entry, 'text', '').strip()
            } for entry in transcript_data]

            return {
                'status': 'success',
                'video_id': video_id,
                'video_url': f'https://www.youtube.com/watch?v={video_id}',
                'thumbnail_url': f'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
                'transcript': formatted,
                'transcript_type': 'auto-generated' if transcript.is_generated else 'manual',
                'language': transcript.language,
                'language_code': transcript.language_code,
                'total_segments': len(formatted)
            }

        except TranscriptsDisabled:
            api.abort(403, "Transcripts are disabled")
        except VideoUnavailable:
            api.abort(404, "Video is unavailable or private")
        except Exception as e:
            api.abort(500, f"Internal server error: {str(e)}")
