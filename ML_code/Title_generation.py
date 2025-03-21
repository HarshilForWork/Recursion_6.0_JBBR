import json
import subprocess
import pandas as pd
import re
from collections import Counter

def extract_caption_from_json(file_path):
    """
    Extracts and concatenates 'text' fields from a JSON file to form a caption.
    """
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
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

def generate_youtube_metadata(caption, trending_words, frequent_names):
    """
    Generates a title, description with hashtags, and tags for a YouTube Short
    using the Qwen2.5:3B model via Ollama based on the provided caption.
    """
    prompt = f"""
    You are an AI assistant specializing in generating YouTube Shorts metadata. 
    Given a transcript from a YouTube Short and trending words, generate:
    1. A catchy title that is engaging and relevant.
    2. A short description that includes relevant details and hashtags and keep it small.
    3. A list of tags that follow these rules:
    - Keep them simple and relevant (no overly complex phrases).
    - Include names of people who are mentioned frequently in the transcript.
    - Provide the overall genre/topic of the video.
    - Include loads of relevant tags.
    - You have to include spaces in tags wherever neccessary.
    - Include trending words from the CSV file.

    **Transcript:**  
    {caption[:1000]}  # Truncated to avoid token limits

    **Trending Words:**  
    {", ".join(trending_words)}

    **Frequent Names:**  
    {", ".join(frequent_names)}

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

if __name__ == "__main__":
    # File paths
    json_path = "output.json"
    csv_path = "output.csv"

    # Extract caption from JSON
    caption = extract_caption_from_json(json_path)

    # Extract trending words from CSV
    trending_words = extract_trending_words(csv_path)

    # Extract frequently mentioned names from transcript
    frequent_names = extract_frequent_names(caption)

    if caption:
        # Generate YouTube Shorts metadata
        metadata = generate_youtube_metadata(caption, trending_words, frequent_names)

        # Add additional tags
        if "tags" in metadata:
            metadata["tags"].extend(["Trending", "Youtube shorts", "YoutubeShorts"])

        # Output the result in JSON format
        if metadata:
            print(json.dumps(metadata, indent=4))
            # Also save to a file
            with open("metadata.json", "w") as f:
                json.dump(metadata, f, indent=4)
            print("Metadata saved to metadata.json")
        else:
            print("Failed to generate metadata.")
    else:
        print("No caption could be extracted from the JSON file.")