import os
import subprocess
import sys
import glob

# Define the folder containing the clips.
clips_folder = os.path.join(".", ".output", "clips")

# Define the ffmpeg filter: scale to 3:4 then pad to 9:16.
vf_filter = (
    "scale='if(gt(a,4/3),ih*4/3,iw)':'if(lt(a,4/3),iw*3/4,ih)',"
    "pad=w=iw:h=iw*16/9:x=0:y=(oh-ih)/2:color=black"
)

def process_and_replace(file_path):
    """
    Processes a single video file using ffmpeg to apply the scaling and padding,
    then replaces the original file with the processed file.
    """
    # Prepare temporary output file path.
    directory, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)
    temp_output = os.path.join(directory, f"{name}_temp{ext}")
    
    # Build the ffmpeg command.
    cmd = [
        "ffmpeg",
        "-i", file_path,
        "-vf", vf_filter,
        "-c:a", "copy",
        temp_output
    ]
    
    print(f"Processing {file_path}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Processed video saved temporarily to: {temp_output}")
    except subprocess.CalledProcessError as e:
        print("An error occurred during processing:")
        print("Return code:", e.returncode)
        print("Standard Output:", e.stdout)
        print("Error Output:", e.stderr)
        return False

    # Replace the original file with the processed one.
    try:
        os.replace(temp_output, file_path)
        print(f"Replaced original file with processed video: {file_path}")
    except Exception as e:
        print(f"Error replacing file {file_path}: {str(e)}")
        return False
    return True

def process_all_clips(folder):
    """
    Processes all mp4 files in the given folder.
    """
    mp4_files = glob.glob(os.path.join(folder, "*.mp4"))
    if not mp4_files:
        print("No mp4 files found in the folder.")
        return
    
    for mp4_file in mp4_files:
        success = process_and_replace(mp4_file)
        if not success:
            print(f"Failed processing: {mp4_file}")
        else:
            print(f"Successfully processed: {mp4_file}")

if __name__ == '__main__':
    process_all_clips(clips_folder)
