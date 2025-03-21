import pandas as pd
df = pd.read_csv('output.csv')
df_json = pd.read_json('output.json')

top_5_words = df.nlargest(5, 'Value')['Item']

word_counts = {word: df_json['text'].str.contains(rf'\b{word}\b', case=False).sum() for word in top_5_words}
word_occurrences = {}
for word in top_5_words:
    matches = df_json[df_json['text'].str.contains(word, case=False, na=False)]
    word_occurrences[word] = matches[['text', 'start', 'duration']].to_dict('records')

time_range = 15

adjusted_timestamps = {}

for word, occurrences in word_occurrences.items():
    adjusted_timestamps[word] = []
    for occurrence in occurrences:
        start_time = occurrence['start']
        lower_bound = start_time - time_range
        upper_bound = start_time + time_range

        nearest_floor = df_json[df_json['start'] <= lower_bound]['start'].max() if not df_json[df_json['start'] <= lower_bound].empty else lower_bound
        nearest_ceil = df_json[df_json['start'] >= upper_bound]['start'].min() if not df_json[df_json['start'] >= upper_bound].empty else upper_bound

        adjusted_timestamps[word].append({
            'original_start': start_time,
            'lower_bound': nearest_floor,
            'upper_bound': nearest_ceil
        })

from moviepy.video.io.VideoFileClip import VideoFileClip
import os
import yt_dlp

def download_youtube_video(url, output_dir='.'):
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
    try:
        video = VideoFileClip(source_path)
        for word, timestamps in timestamps_dict.items():
            for i, timestamp in enumerate(timestamps):
                start_time = timestamp['lower_bound']
                end_time = timestamp['upper_bound']
                output_file = os.path.join(output_dir, f"trimmed_video_{word}_{i + 1}.mp4")

                trimmed_video = video.subclipped(start_time, end_time)
                trimmed_video.write_videofile(output_file, codec="libx264", audio_codec="aac")
                trimmed_video.close()
                
                print(f"Created {output_file}")
        
        video.close()
    
    except Exception as e:
        print(f"Error creating trimmed videos: {str(e)}")
        import traceback
        traceback.print_exc()

youtube_url = 'https://www.youtube.com/watch?v=dLuQ1wSJACU'
output_directory = '.'

source_video_path = download_youtube_video(youtube_url, output_directory)

if source_video_path:
    create_trimmed_videos(source_video_path, adjusted_timestamps, output_directory)
    
    os.remove(source_video_path)
    print(f"Removed temporary source file: {source_video_path}")


