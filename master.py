import os
import sys
import subprocess
import pandas as pd

def main():
    print("=" * 50)
    print("🎥 YouTube Video Keyword Analyzer")
    print("=" * 50)
    
    # Get YouTube URL from user
    youtube_url = input("Enter YouTube URL: ").strip()
    if not youtube_url:
        youtube_url = "https://www.youtube.com/watch?v=6W-ncSvNVe0"
        print(f"Using default URL: {youtube_url}")
    
    output_path = "output"
    
    # Step 1: Run caption_extractor.py
    print("\n📝 Step 1: Extracting captions...")
    try:
        subprocess.run([sys.executable, "caption_extractor.py", youtube_url, output_path], check=True)
        print("✅ Caption extraction complete")
    except subprocess.CalledProcessError:
        print("❌ Caption extraction failed. Exiting.")
        return
    
    # Check if custom_stop_words.txt exists, if not create it
    if not os.path.exists("custom_stop_words.txt"):
        with open("custom_stop_words.txt", 'w') as f:
            default_stop_words = [
                "the", "and", "a", "to", "of", "in", "is", "it", "that", "you", 
                "for", "on", "with", "as", "are", "be", "this", "was", "have", "by",
                "um", "uh", "ah", "oh", "mm", "hmm", "gonna", "wanna", "like", "just"
            ]
            f.write("\n".join(default_stop_words))
        print("📄 Created default custom stop words file")
    
    # Step 2: Run trend_analyzer.py
    print("\n📊 Step 2: Analyzing keyword trends...")
    try:
        subprocess.run([sys.executable, "trend_analyzer.py"], check=True)
        print("✅ Trend analysis complete")
    except subprocess.CalledProcessError:
        print("❌ Trend analysis failed. Exiting.")
        return
    
    # Display top keywords from output.csv
    try:
        df = pd.read_csv('output.csv')
        top_keywords = df.nlargest(5, 'Value')
        print("\nTop 5 keywords found:")
        for i, (_, row) in enumerate(top_keywords.iterrows(), 1):
            print(f"{i}. {row['Item']} (score: {row['Value']:.2f})")
    except Exception as e:
        print(f"Could not read keyword results: {str(e)}")
    
    # Step 3: Get time range for timestamp.py
    time_range = input("\nEnter time range in seconds around each keyword (default: 15): ").strip()
    if not time_range or not time_range.isdigit():
        time_range = 15
    else:
        time_range = int(time_range)
    
    # Step 4: Run timestamp.py
    print(f"\n🎬 Step 3: Processing video segments with time range of {time_range} seconds...")
    try:
        subprocess.run([sys.executable, "timestamp.py", youtube_url, str(time_range)], check=True)
        print("✅ Video processing complete")
    except subprocess.CalledProcessError:
        print("❌ Video processing failed. Exiting.")
        return
    
    print("\n" + "=" * 50)
    print("✅ Process completed successfully!")
    print("=" * 50)
    print("Video clips have been saved in the current directory.")

if __name__ == "__main__":
    main()