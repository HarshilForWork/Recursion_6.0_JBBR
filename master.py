import os
import sys
import subprocess
import pandas as pd
import glob

def process_all_clips(folder):
    """
    Processes all mp4 files in the given folder by applying the scaling and padding filter
    (scale to 3:4 then pad to 9:16) using ffmpeg. The processed video replaces the original file.
    """
    # Define the ffmpeg filter
    vf_filter = (
        "scale='if(gt(a,4/3),ih*4/3,iw)':'if(lt(a,4/3),iw*3/4,ih)',"
        "pad=w=iw:h=iw*16/9:x=0:y=(oh-ih)/2:color=black"
    )
    
    mp4_files = glob.glob(os.path.join(folder, "*.mp4"))
    if not mp4_files:
        print("No mp4 files found in the folder to process for reframing.")
        return
    
    for file_path in mp4_files:
        directory, filename = os.path.split(file_path)
        name, ext = os.path.splitext(filename)
        temp_output = os.path.join(directory, f"{name}_temp{ext}")
        
        cmd = [
            "ffmpeg",
            "-i", file_path,
            "-vf", vf_filter,
            "-c:a", "copy",
            temp_output
        ]
        
        print(f"Reframing {file_path}...")
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Replace the original file with the reframed video.
            os.replace(temp_output, file_path)
            print(f"Replaced original clip with meme-style video: {file_path}")
        except subprocess.CalledProcessError as e:
            print("An error occurred during reframing:")
            print("Return code:", e.returncode)
            print("Standard Output:", e.stdout)
            print("Error Output:", e.stderr)
        except Exception as e:
            print(f"Error replacing file {file_path}: {str(e)}")
            

def main():
    print("=" * 50)
    print("🎥 YouTube Video Keyword Analyzer")
    print("=" * 50)
    
    # Get YouTube URL from user
    youtube_url = input("Enter YouTube URL: ").strip()
    if not youtube_url:
        youtube_url = "https://www.youtube.com/watch?v=S8nNhY-XVXU"
        print(f"Using default URL: {youtube_url}")
    
    # Get top N keywords from user
    top_n = input("Enter number of top keywords to process (default: 5): ").strip()
    if not top_n or not top_n.isdigit():
        top_n = 5
    else:
        top_n = int(top_n)
    print(f"Processing top {top_n} keywords")
    
    # Get time range from user
    time_range = input("Enter time range in seconds around each keyword (default: 15): ").strip()
    if not time_range or not time_range.isdigit():
        time_range = 15
    else:
        time_range = int(time_range)
    print(f"Using time range of {time_range} seconds")
    
    # Create a single output directory
    output_dir = ".output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    caption_output = os.path.join(output_dir, "captions.txt")
    
    # Step 1: Run caption_extractor.py
    print("\n📝 Step 1: Extracting captions...")
    try:
        subprocess.run([sys.executable, "caption_extractor.py", youtube_url, caption_output], check=True)
        print("✅ Caption extraction complete")
    except subprocess.CalledProcessError:
        print("❌ Caption extraction failed. Exiting.")
        return
    
    # Check if custom_stop_words.txt exists, if not create it
    custom_stop_words_path = os.path.join(output_dir, "custom_stop_words.txt")
    if not os.path.exists(custom_stop_words_path):
        with open(custom_stop_words_path, 'w') as f:
            default_stop_words = [
                "the", "and", "a", "to", "of", "in", "is", "it", "that", "you", 
                "for", "on", "with", "as", "are", "be", "this", "was", "have", "by",
                "um", "uh", "ah", "oh", "mm", "hmm", "gonna", "wanna", "like", "just"
            ]
            f.write("\n".join(default_stop_words))
        print("📄 Created default custom stop words file")
    
    # Step 2: Run trend_analyzer.py
    print("\n📊 Step 2: Analyzing keyword trends...")
    json_path = os.path.join(output_dir, "captions.txt.json")  
    output_csv = os.path.join(output_dir, "keywords.csv")
    try:
        subprocess.run([
            sys.executable, 
            "trend_analyzer.py", 
            json_path,
            custom_stop_words_path,
            output_csv
        ], check=True)
        print("✅ Trend analysis complete")
    except subprocess.CalledProcessError:
        print("❌ Trend analysis failed. Exiting.")
        return
    
    # Display top keywords from output.csv
    try:
        df = pd.read_csv(output_csv)
        top_keywords = df.nlargest(top_n, 'Value')
        print("\nTop keywords found:")
        for i, (_, row) in enumerate(top_keywords.iterrows(), 1):
            print(f"{i}. {row['Item']} (score: {row['Value']:.2f})")
    except Exception as e:
        print(f"Could not read keyword results: {str(e)}")
    
    # Step 3: Run timestamp.py with all parameters
    clips_dir = os.path.join(output_dir, "clips")
    print(f"\n🎬 Step 3: Processing video segments...")
    try:
        subprocess.run([
            sys.executable, 
            "timestamp.py", 
            youtube_url, 
            str(time_range),
            clips_dir,
            output_csv,
            json_path,
            str(top_n)
        ], check=True)
        print("✅ Video processing complete")
    except subprocess.CalledProcessError:
        print("❌ Video processing failed. Exiting.")
        return
    
    # Step 4: Reframe all clips to meme-style (overwrite original files)
    print(f"\n🔄 Step 4: Reframing video clips to meme-style...")
    process_all_clips(clips_dir)
    
    # Step 5: Generate titles and metadata for clips
    print(f"\n📝 Step 5: Generating titles and metadata for clips...")
    adjusted_timestamps_csv = os.path.join(output_dir, "adjusted_timestamps.csv")
    metadata_dir = os.path.join(output_dir, "metadata")
    
    try:
        subprocess.run([
            sys.executable,
            "title_generation.py",
            adjusted_timestamps_csv,
            json_path,
            output_csv,
            metadata_dir
        ], check=True)
        print("✅ Title generation complete")
    except subprocess.CalledProcessError as e:
        print(f"❌ Title generation failed: {e}")
    except Exception as e:
        print(f"❌ Title generation failed with error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("✅ Process completed successfully!")
    print("=" * 50)
    print(f"All outputs have been saved to the '{output_dir}' directory:")
    print(f"- Captions: {caption_output}")
    print(f"- Captions JSON: {json_path}")
    print(f"- Keywords data: {output_csv}")
    print(f"- Video clips: {clips_dir}")
    print(f"- Adjusted timestamps: {adjusted_timestamps_csv}")
    print(f"- Metadata: {metadata_dir}")

if __name__ == "__main__":
    main()