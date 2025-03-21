from youtube_transcript_api import YouTubeTranscriptApi
import json
import sys
import re

def extract_video_id(url):
    """
    Extract the video ID from a YouTube URL.
    Supports various YouTube URL formats.
    """
    # Patterns for YouTube URLs
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',  # Standard and shortened
        r'(?:embed\/)([0-9A-Za-z_-]{11})',  # Embed URLs
        r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})'  # youtu.be URLs
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def download_captions(video_url, output_file=None, languages=['en']):
    """
    Download captions from a YouTube video.
    
    Args:
        video_url (str): The YouTube video URL or ID
        output_file (str, optional): File to save captions to. If None, prints to console.
        languages (list, optional): List of language codes to try, in order of preference.
    
    Returns:
        list: The transcript as a list of dictionaries.
    """
    # Check if input is a URL or an ID
    video_id = extract_video_id(video_url)
    
    # If extraction failed, assume the input is already a video ID
    if not video_id:
        video_id = video_url
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        
        # Format the transcript
        formatted_transcript = ""
        for entry in transcript:
            start_time = entry['start']
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            text = entry['text']
            formatted_transcript += f"[{minutes:02d}:{seconds:02d}] {text}\n"
        
        # Output the transcript
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_transcript)
                
            # Also save the raw JSON for potential further processing
            with open(f"{output_file}.json", 'w', encoding='utf-8') as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
                
            print(f"Captions saved to {output_file} and {output_file}.json")
        else:
            print(formatted_transcript)
            
        return transcript
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # If run from command line
    if len(sys.argv) > 1:
        video_url = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        download_captions(video_url, output_file)
    else:
        # Interactive mode
        print("YouTube Caption Downloader")
        print("-------------------------")
        video_url = 'https://www.youtube.com/watch?v=dLuQ1wSJACU'
        output_file = "output"
        
        if not output_file:
            output_file = None
            
        download_captions(video_url, output_file)