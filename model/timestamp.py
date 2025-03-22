import pandas as pd
import sys
import os
from moviepy.video.io.VideoFileClip import VideoFileClip
import yt_dlp
from caption_extractor import extract_video_id

def process_video(youtube_url, time_range=15, output_dir='clips', keywords_csv='output.csv', captions_json='output.json', top_n=5):
    """
    Process a YouTube video to create clips around keywords
    
    Args:
        youtube_url (str): YouTube video URL or ID
        time_range (int): Time range in seconds to capture around keywords
        output_dir (str): Directory to save the clips
        keywords_csv (str): Path to keywords CSV file
        captions_json (str): Path to captions JSON file
        top_n (int): Number of top keywords to process
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Load data files
    try:
        df = pd.read_csv(keywords_csv)
        df_json = pd.read_json(captions_json)
    except Exception as e:
        print(f"Error loading data files: {str(e)}")
        return False
    
    # Get top words
    top_words = df.nlargest(top_n, 'Value')['Item']
    print(f"Processing clips for top {top_n} keywords: {list(top_words)}")
    
    # Find first occurrence of each top word
    word_occurrences = {}
    for word in top_words:
        match = df_json[df_json['text'].str.contains(word, case=False, na=False)].head(1)
        if not match.empty:
            word_occurrences[word] = match[['text', 'start', 'duration']].to_dict('records')
    
    # Calculate adjusted timestamps
    adjusted_timestamps = []
    for word, occurrences in word_occurrences.items():
        for occurrence in occurrences:
            start_time = occurrence['start']
            lower_bound = max(0, start_time - time_range)
            upper_bound = start_time + time_range
    
            nearest_floor = df_json[df_json['start'] <= lower_bound]['start'].max() if not df_json[df_json['start'] <= lower_bound].empty else lower_bound
            nearest_ceil = df_json[df_json['start'] >= upper_bound]['start'].min() if not df_json[df_json['start'] >= upper_bound].empty else upper_bound
    
            adjusted_timestamps.append({
                'word': word,
                'original_start': start_time,
                'lower_bound': nearest_floor,
                'upper_bound': nearest_ceil
            })
    
    # Save adjusted timestamps to a CSV file
    timestamps_df = pd.DataFrame(adjusted_timestamps)
    timestamps_csv_path = os.path.join('.output', 'adjusted_timestamps.csv')
    timestamps_df.to_csv(timestamps_csv_path, index=False)
    print(f"Adjusted timestamps saved to {timestamps_csv_path}")
    
    # Download the YouTube video
    source_path = download_youtube_video(youtube_url, output_dir)
    if not source_path:
        return False
    
    # Group adjusted timestamps by word
    grouped_timestamps = {}
    for entry in adjusted_timestamps:
        word = entry['word']
        if word not in grouped_timestamps:
            grouped_timestamps[word] = []
        grouped_timestamps[word].append(entry)
    
    # Create the trimmed videos
    success = create_trimmed_videos(source_path, grouped_timestamps, output_dir)
    
    # Clean up the source video
    try:
        os.remove(source_path)
        print(f"Removed temporary source file: {source_path}")
    except Exception as e:
        print(f"Could not remove source file: {str(e)}")
    
    return success

def download_youtube_video(url, output_dir='.'):
    """
    Download a YouTube video
    
    Args:
        url (str): YouTube URL or ID
        output_dir (str): Directory to save the video
    
    Returns:
        str: Path to the downloaded video file
    """
    # Extract video ID if URL is provided
    video_id = extract_video_id(url)
    if video_id:
        url = f"https://www.youtube.com/watch?v={video_id}"
    
    print(f"Downloading video from {url}...")
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(output_dir, 'source_video.%(ext)s')
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            ext = info.get('ext', 'mp4')
            source_path = os.path.join(output_dir, f'source_video.{ext}')
            return source_path
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_trimmed_videos(source_path, timestamps_dict, output_dir='.'):
    """
    Create trimmed video clips from a source video
    
    Args:
        source_path (str): Path to the source video
        timestamps_dict (dict): Dictionary of timestamps for each keyword
        output_dir (str): Directory to save the clips
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        video = VideoFileClip(source_path)
        for word, timestamps in timestamps_dict.items():
            for i, timestamp in enumerate(timestamps):
                start_time = timestamp['lower_bound']
                end_time = timestamp['upper_bound']
                output_file = os.path.join(output_dir, f"{word}_clip_{i + 1}.mp4")
    
                trimmed_video = video.subclipped(start_time, end_time)
                trimmed_video.write_videofile(output_file, codec="libx264", audio_codec="aac")
                trimmed_video.close()
                
                print(f"Created {output_file}")
        
        video.close()
        return True
    
    except Exception as e:
        print(f"Error creating trimmed videos: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Default values
    youtube_url = 'https://www.youtube.com/watch?v=dLuQ1wSJACU'
    time_range = 15
    output_dir = 'clips'
    keywords_csv = 'output.csv'
    captions_json = 'output.json'
    top_n = 5
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        youtube_url = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            time_range = int(sys.argv[2])
        except ValueError:
            print(f"Invalid time range: {sys.argv[2]}. Using default: 15 seconds")
    if len(sys.argv) > 3:
        output_dir = sys.argv[3]
    if len(sys.argv) > 4:
        keywords_csv = sys.argv[4]
    if len(sys.argv) > 5:
        captions_json = sys.argv[5]
    if len(sys.argv) > 6:
        try:
            top_n = int(sys.argv[6])
        except ValueError:
            print(f"Invalid top_n: {sys.argv[6]}. Using default: 5 keywords")
    
    process_video(youtube_url, time_range, output_dir, keywords_csv, captions_json, top_n)