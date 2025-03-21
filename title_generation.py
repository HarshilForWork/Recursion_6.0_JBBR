import json
import subprocess
import pandas as pd
import re
import os
import sys
from collections import Counter
from pymongo import MongoClient

def extract_caption_from_json(file_path, lower_bound=None, upper_bound=None):
    """
    Extracts and concatenates 'text' fields from a JSON file to form a caption.
    If lower_bound and upper_bound are provided, only includes entries within that time range.
    Works with output.json format that contains 'start' and 'duration' fields.
    """
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            
            if lower_bound is not None and upper_bound is not None:
                # Filter entries by timestamp if bounds are provided
                filtered_entries = []
                for entry in data:
                    # Calculate end time by adding start + duration
                    if 'start' in entry and 'duration' in entry:
                        start_time = float(entry['start'])
                        end_time = start_time + float(entry['duration'])
                        
                        # Check if the entry falls within the bounds
                        # Use overlap logic: entry starts before upper_bound AND ends after lower_bound
                        if start_time <= upper_bound and end_time >= lower_bound:
                            filtered_entries.append(entry)
                
                texts = [entry.get('text', '') for entry in filtered_entries if 'text' in entry]
            else:
                # If no bounds provided, use all entries
                texts = [entry.get('text', '') for entry in data if 'text' in entry]
                
            caption = ' '.join(texts)
            return caption
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return ""
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} is not a valid JSON file.")
        return ""

def extract_trending_words(csv_path, top_n=5):
    """
    Extracts the top N trending words from the CSV file.
    """
    try:
        df = pd.read_csv(csv_path)
        trending_words = df.nlargest(top_n, "Value")["Item"].tolist()
        return trending_words
    except FileNotFoundError:
        print(f"Error: The file {csv_path} was not found.")
        return []
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []

def extract_frequent_names(transcript, min_mentions=2):
    """
    Extracts frequently mentioned names from the transcript.
    Assumes names are capitalized words appearing multiple times.
    """
    words = transcript.split()
    capitalized_words = [word for word in words if word.istitle()]  # Get capitalized words
    name_counts = Counter(capitalized_words)  # Count occurrences

    # Select names that appear at least 'min_mentions' times
    frequent_names = [name for name, count in name_counts.items() if count >= min_mentions]
    return frequent_names[:5]  # Limit to top 5 names

def load_adjusted_timestamps(csv_path):
    """
    Loads word, lower_bound, and upper_bound from the adjusted_timestamps.csv file.
    Returns a list of dictionaries containing this information.
    """
    try:
        df = pd.read_csv(csv_path)
        # Ensure the required columns exist
        required_columns = ['word', 'lower_bound', 'upper_bound']
        if not all(col in df.columns for col in required_columns):
            missing = [col for col in required_columns if col not in df.columns]
            print(f"Error: Missing columns in timestamps CSV: {missing}")
            return []
            
        # Convert DataFrame to list of dictionaries
        timestamp_data = df[required_columns].to_dict('records')
        return timestamp_data
    except FileNotFoundError:
        print(f"Error: The file {csv_path} was not found.")
        return []
    except Exception as e:
        print(f"Error reading timestamps CSV file: {e}")
        return []

def generate_youtube_metadata(caption, trending_words, frequent_names, word):
    """
    Generates a title, description with hashtags, and tags for a YouTube Short
    using the Qwen2.5:3B model via Ollama based on the provided caption.
    Includes the word in the metadata generation process.
    """
    prompt = f"""
    You are an AI assistant specializing in generating YouTube Shorts metadata. 
    Given a transcript from a YouTube Short, trending words, and a specific focus word, generate:
    1. A catchy title that is engaging and relevant. Include the word "{word}" if appropriate.
    2. A short description that includes relevant details and hashtags and keep it small.
    3. A list of tags that follow these rules:
    - Keep them simple and relevant (no overly complex phrases).
    - Include names of people who are mentioned frequently in the transcript.
    - Provide the overall genre/topic of the video.
    - Include loads of relevant tags.
    - You have to include spaces in tags wherever necessary.
    - Include trending words from the CSV file.
    - Include the word "{word}" as one of the tags.

    **Transcript:**  
    {caption[:1000]}  # Truncated to avoid token limits

    **Trending Words:**  
    {", ".join(trending_words)}

    **Frequent Names:**  
    {", ".join(frequent_names)}

    **Focus Word:**
    {word}

    **Output Format (JSON):**  
    {{
        "title": "...",
        "description": "...",
        "tags": ["...", "...", "..."]  # Simple tags, including names and topic/genre
    }}

    Generate engaging and SEO-friendly metadata. Your response should be valid JSON only.
    """

    try:
        # For Ollama, we need to use JSON parameters to set temperature
        # Create a JSON parameter object for Ollama
        ollama_params = json.dumps({
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "options": {
                "temperature": 0.1
            }
        })

        # Use the Ollama API via curl to set temperature
        result = subprocess.run(
            ['curl', '-s', '-X', 'POST', 'http://localhost:11434/api/generate', 
             '-d', ollama_params, '-H', 'Content-Type: application/json'],
            capture_output=True,
            text=True
        )

        # Check if the command was successful
        if result.returncode != 0:
            print(f"Error: Ollama API call failed with return code {result.returncode}")
            print(f"stderr: {result.stderr}")
            return {}

        # Parse the Ollama API response (it's a series of JSON objects)
        response_lines = result.stdout.strip().split('\n')
        full_response = ""
        
        for line in response_lines:
            try:
                response_obj = json.loads(line)
                if "response" in response_obj:
                    full_response += response_obj["response"]
            except json.JSONDecodeError:
                pass
        
        # Try multiple approaches to extract valid JSON
        try:
            # First attempt: try to parse the entire response as JSON
            metadata = json.loads(full_response)
            return metadata
        except json.JSONDecodeError:
            # Second attempt: look for JSON object with regex
            # This pattern finds the outermost JSON object
            json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
            matches = re.findall(json_pattern, full_response, re.DOTALL)
            
            for match in matches:
                try:
                    metadata = json.loads(match)
                    # Validate that the extracted JSON has the expected structure
                    if all(key in metadata for key in ["title", "description", "tags"]):
                        return metadata
                except json.JSONDecodeError:
                    continue
            
            # If we've tried all matches and none worked, try a more aggressive approach
            # Look for anything that might be JSON-like with the required fields
            title_match = re.search(r'"title"\s*:\s*"([^"]*)"', full_response)
            desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', full_response)
            tags_match = re.search(r'"tags"\s*:\s*\[(.*?)\]', full_response, re.DOTALL)
            
            if title_match and desc_match and tags_match:
                try:
                    # Construct a valid JSON manually
                    tags_str = tags_match.group(1).strip()
                    # Clean up the tags string
                    tags_str = re.sub(r'"\s*,\s*"', '","', tags_str)
                    if not tags_str.startswith('"'):
                        tags_str = '"' + tags_str
                    if not tags_str.endswith('"'):
                        tags_str = tags_str + '"'
                    
                    manual_json = f'{{"title": "{title_match.group(1)}", "description": "{desc_match.group(1)}", "tags": [{tags_str}]}}'
                    return json.loads(manual_json)
                except Exception:
                    pass
            
            print("Error: Couldn't extract valid JSON from model response.")
            print(f"Raw output excerpt: {full_response[:200]}...")
            return {}

    except Exception as e:
        print(f"An error occurred: {e}")
        return {}

def process_clips_and_generate_metadata(timestamps_csv, json_path, trending_csv, output_dir="clip_metadata"):
    """
    Processes each clip from the adjusted_timestamps.csv, extracts the relevant caption portion,
    and generates metadata for each clip with naming convention word_clip_1.
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load timestamp data
    timestamp_data = load_adjusted_timestamps(timestamps_csv)
    
    if not timestamp_data:
        print("No timestamp data found. Exiting.")
        return
    
    # Extract trending words from CSV
    trending_words = extract_trending_words(trending_csv)
    
    # Process each clip
    all_metadata = {}
    
    for _, clip_data in enumerate(timestamp_data):
        word = clip_data['word']
        lower_bound = clip_data['lower_bound']
        upper_bound = clip_data['upper_bound']
        
        # Always use "_1" at the end of the clip ID
        clip_id = f"{word}_clip_1"
        
        print(f"Processing clip: {clip_id}")
        print(f"Time range: {lower_bound} to {upper_bound}")
        
        # Extract caption for this specific time range
        caption = extract_caption_from_json(json_path, lower_bound, upper_bound)
        
        if not caption:
            print(f"Warning: No caption extracted for clip {clip_id}. Skipping.")
            continue
        
        # Extract frequently mentioned names from this clip's transcript
        frequent_names = extract_frequent_names(caption)
        
        # Generate metadata for this clip
        metadata = generate_youtube_metadata(caption, trending_words, frequent_names, word)
        
        # Add additional tags
        if "tags" in metadata:
            metadata["tags"].extend(["Trending", "Youtube shorts", "YoutubeShorts", word])
        
        # Save to all_metadata dictionary
        all_metadata[clip_id] = metadata
        
        # Save individual clip metadata to file
        clip_file_path = os.path.join(output_dir, f"{clip_id}.json")
        with open(clip_file_path, "w") as f:
            json.dump(metadata, f, indent=4)
        
        print(f"Saved metadata for {clip_id} to {clip_file_path}")
    
    # Save combined metadata to a single file
    combined_file_path = os.path.join(output_dir, "all_clips_metadata.json")
    with open(combined_file_path, "w") as f:
        json.dump(all_metadata, f, indent=4)
    
    print(f"Saved combined metadata to {combined_file_path}")
    return all_metadata

def push_metadata_to_mongodb(metadata, uri, db_name, collection_name):
    """
    Pushes the generated metadata to the specified MongoDB collection.
    """
    try:
        client = MongoClient(uri)
        db = client[db_name]
        collection = db[collection_name]
        
        # Add clip name to each metadata entry
        documents_to_insert = []
        for clip_name, data in metadata.items():
            document = data.copy()
            document['clip_name'] = clip_name
            documents_to_insert.append(document)
        
        if documents_to_insert:
            collection.insert_many(documents_to_insert)
            print(f"Metadata pushed to MongoDB collection: {collection_name}")
        else:
            print("No metadata to push to MongoDB.")
    except Exception as e:
        print(f"Error pushing metadata to MongoDB: {str(e)}")

if __name__ == "__main__":
    # Check if command-line arguments are provided
    if len(sys.argv) == 5:
        timestamps_csv = sys.argv[1]  # Path to adjusted_timestamps.csv
        json_path = sys.argv[2]      # Path to captions.txt.json
        trending_csv = sys.argv[3]   # Path to keywords.csv
        output_dir = sys.argv[4]     # Directory to save metadata
        
        print(f"Using parameters from command line:")
        print(f"Timestamps CSV: {timestamps_csv}")
        print(f"JSON Path: {json_path}")
        print(f"Trending CSV: {trending_csv}")
        print(f"Output Directory: {output_dir}")
    else:
        # Use default paths if command-line arguments are not provided
        print("Using default file paths")
        timestamps_csv = r".output/adjusted_timestamps.csv"
        json_path = r".output/captions.txt.json"
        trending_csv = r".output/keywords.csv"
        output_dir = r".output/metadata"
    
    # Process all clips and generate metadata
    metadata = process_clips_and_generate_metadata(timestamps_csv, json_path, trending_csv, output_dir)
    
    # MongoDB connection details (optional)
    try:
        # Only attempt to push to MongoDB if metadata was generated
        if metadata:
            mongo_uri = "mongodb+srv://shilankfans07:jbbr123@trimly.3hglc.mongodb.net/?retryWrites=true&w=majority&appName=trimly"
            db_name = "test"
            collection_name = "video_metadata"
            push_metadata_to_mongodb(metadata, mongo_uri, db_name, collection_name)
            
    except Exception as e:
        print(f"Error with MongoDB operation: {str(e)}")