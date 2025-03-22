import os
import re
import csv
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import shutil

def main():
    # Define paths
    clips_folder = ".output/clips"
    timestamps_file = ".output/adjusted_timestamps.csv"
    captions_file = ".output/captions.txt.json"

    # Create output directory if it doesn't exist
    os.makedirs(clips_folder, exist_ok=True)

    # Load timestamps
    word_timestamps = {}
    try:
        with open(timestamps_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                word_timestamps[row['word']] = {
                    'lower_bound': float(row['lower_bound']),
                    'upper_bound': float(row['upper_bound'])
                }
    except FileNotFoundError:
        print(f"Error: Timestamps file not found at {timestamps_file}")
        exit(1)

    # Load captions
    try:
        with open(captions_file, 'r', encoding='utf-8') as f:
            captions_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Captions file not found at {captions_file}")
        exit(1)

    # Font for subtitles
    font_path = "arial.ttf"  # Change to an existing font path on your system
    font_size = 24  # Increased font size for better visibility
    
    # Try to load the font, or fall back to default
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        print(f"Warning: Font {font_path} not found. Using default font.")
        font = ImageFont.load_default()

    # Define colors for poppy effect - using more vibrant colors
    colors = ["#FF3366", "#33CCFF", "#FFCC00", "#66FF33", "#FF9900"]

    # Process each clip
    processed_count = 0
    for clip in os.listdir(clips_folder):
        if clip.endswith('.mp4'):
            word_match = re.match(r'(\w+)_clip_\d+\.mp4', clip)
            if word_match:
                word = word_match.group(1)
                if word in word_timestamps:
                    lower_bound = word_timestamps[word]['lower_bound']
                    upper_bound = word_timestamps[word]['upper_bound']

                    # Extract relevant captions
                    relevant_captions = []
                    for caption in captions_data:
                        caption_start = caption['start']
                        caption_end = caption_start + caption['duration']

                        if (lower_bound <= caption_start <= upper_bound) or \
                           (lower_bound <= caption_end <= upper_bound) or \
                           (caption_start <= lower_bound and caption_end >= upper_bound):

                            adjusted_start = max(0, caption_start - lower_bound)
                            adjusted_duration = min(upper_bound - lower_bound, caption_end - lower_bound) - adjusted_start

                            if adjusted_duration > 0:
                                relevant_captions.append({
                                    'text': caption['text'],
                                    'start': adjusted_start,
                                    'duration': adjusted_duration
                                })

                    # Create temporary file paths
                    input_video_path = os.path.join(clips_folder, clip)
                    temp_output_path = os.path.join(clips_folder, f"temp_{clip}")
                    
                    # Only process if there are captions to add
                    if relevant_captions:
                        # Open video file
                        cap = cv2.VideoCapture(input_video_path)
                        if not cap.isOpened():
                            print(f"Error: Could not open video file {input_video_path}")
                            continue
                            
                        fps = int(cap.get(cv2.CAP_PROP_FPS))
                        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        
                        # Use ffmpeg to extract audio from the original video
                        temp_audio_path = os.path.join(clips_folder, f"temp_audio_{os.path.splitext(clip)[0]}.aac")
                        os.system(f'ffmpeg -i "{input_video_path}" -vn -acodec copy "{temp_audio_path}" -y')

                        # Create video writer
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                        out = cv2.VideoWriter(temp_output_path, fourcc, fps, (frame_width, frame_height))

                        frame_idx = 0
                        while cap.isOpened():
                            ret, frame = cap.read()
                            if not ret:
                                break

                            current_time = frame_idx / fps  # Convert frame index to seconds

                            # Check if any caption should be displayed at this time
                            for cap_text in relevant_captions:
                                start_time = cap_text['start']
                                end_time = cap_text['start'] + cap_text['duration']

                                if start_time <= current_time <= end_time:
                                    pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                                    draw = ImageDraw.Draw(pil_img)

                                    # Get text size and position
                                    text_size = draw.textbbox((0, 0), cap_text['text'], font=font)
                                    text_width = text_size[2] - text_size[0]
                                    text_height = text_size[3] - text_size[1]

                                    # Center horizontally with increased bottom margin (120 pixels from bottom)
                                    x = (frame_width - text_width) // 2
                                    y = frame_height - text_height - 120  # Increased bottom margin

                                    # Compute fade-in and fade-out effect (opacity)
                                    fade_duration = 0.5  # 500ms fade
                                    if current_time - start_time < fade_duration:
                                        alpha = (current_time - start_time) / fade_duration
                                    elif end_time - current_time < fade_duration:
                                        alpha = (end_time - current_time) / fade_duration
                                    else:
                                        alpha = 1.0

                                    alpha = max(0, min(1, alpha))  # Ensure valid range

                                    # Choose a poppy color - convert hex to RGB
                                    color_hex = colors[(frame_idx // 10) % len(colors)]  # Change color more frequently
                                    r = int(color_hex[1:3], 16)
                                    g = int(color_hex[3:5], 16)
                                    b = int(color_hex[5:7], 16)
                                    color = (r, g, b)

                                    # Draw background rectangle with rounded corners effect
                                    padding = 12  # Increased padding
                                    # Semi-transparent background
                                    bg_rect = np.zeros((frame_height, frame_width, 4), dtype=np.uint8)
                                    cv2.rectangle(bg_rect, 
                                                 (x - padding, y - padding), 
                                                 (x + text_width + padding, y + text_height + padding), 
                                                 (0, 0, 0, int(180 * alpha)), 
                                                 -1)
                                    
                                    # Draw shadow for better visibility
                                    shadow_offset = 2
                                    draw.text((x + shadow_offset, y + shadow_offset), cap_text['text'], font=font, fill=(0, 0, 0, int(200 * alpha)))

                                    # Draw main text with pop effect and outline
                                    draw.text((x, y), cap_text['text'], font=font, fill=(255, 255, 255, int(255 * alpha)))
                                    draw.text((x - 1, y - 1), cap_text['text'], font=font, fill=color)

                                    # Convert back to OpenCV format
                                    frame = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                                    break  # Only apply the first matching caption

                            out.write(frame)
                            frame_idx += 1

                        # Close video writers and readers
                        cap.release()
                        out.release()
                        
                        # Combine the video with the audio using ffmpeg
                        final_output_path = input_video_path  # Overwrite the original
                        os.system(f'ffmpeg -i "{temp_output_path}" -i "{temp_audio_path}" -c:v copy -c:a aac -map 0:v:0 -map 1:a:0 "{final_output_path}" -y')
                        
                        # Clean up temporary files
                        if os.path.exists(temp_output_path):
                            os.remove(temp_output_path)
                        if os.path.exists(temp_audio_path):
                            os.remove(temp_audio_path)
                        
                        processed_count += 1
                        print(f"Successfully captioned clip: {clip}")
                    else:
                        print(f"No relevant captions found for {clip}")
                else:
                    print(f"Warning: No timestamp data found for word '{word}' in {clip}")
            else:
                print(f"Filename format not recognized for {clip}")
    
    print(f"Caption processing complete. Added captions to {processed_count} clips.")

if __name__ == "__main__":
    main()