import re
import urllib.request
import json
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

def get_video_title(video_id: str) -> str:
    """Retrieves the title of a YouTube video using oEmbed API."""
    if not video_id:
        return "Unknown Video"
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("title", f"Video {video_id}")
    except Exception:
        return f"Video {video_id}"

def extract_video_id(url: str) -> str:
    """
    Extracts the video ID from a standard YouTube URL.
    Supports formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://youtube.com/shorts/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    """
    if not url:
        return None
    
    # Regular expressions for various YouTube URL patterns
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})',
        r'shorts\/([0-9A-Za-z_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
            
    return None

def get_transcript(video_id: str, preferred_languages: list = ['en', 'hi', 'ml']) -> tuple[str, list]:
    """
    Retrieves the transcript of a YouTube video as a continuous string
    and also returns raw transcript entries for timestamp calculations.
    """
    if not video_id:
        return "Invalid Video ID.", []
        
    try:
        # Instantiate the api client
        api = YouTubeTranscriptApi()
        
        # Retrieve the transcript list
        transcript_list = api.list(video_id)
        
        # Try to find a transcript in one of the preferred languages (or manually generated)
        transcript = None
        for lang in preferred_languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                break
            except Exception:
                continue
                
        # If no preferred language, just get whatever transcript is available
        if not transcript:
            try:
                transcript = transcript_list.find_first_transcript()
            except Exception:
                # If finding first fails, fall back to fetching directly
                fetched_obj = api.fetch(video_id)
                raw_data = fetched_obj.to_raw_data()
                full_text = " ".join([entry['text'] for entry in raw_data])
                return full_text, raw_data
        
        # Fetch the actual transcript entries
        fetched_obj = transcript.fetch()
        raw_data = fetched_obj.to_raw_data()
        full_text = " ".join([entry['text'] for entry in raw_data])
        return full_text, raw_data

    except TranscriptsDisabled:
        return "Error: Transcripts are disabled for this video.", []
    except NoTranscriptFound:
        return "Error: No transcript was found for this video in the requested languages.", []
    except Exception as e:
        return f"Error fetching transcript: {str(e)}", []
