from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_cors import CORS
from pymongo import MongoClient
import os
from dotenv import load_dotenv

import sys
try:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except Exception:
    pass



# Load environment variables from .env file
load_dotenv()

# Set correct static folder for Flask
app = Flask(
    __name__,
    template_folder='webd/templates',
    static_folder='webd/static',
    instance_path='/tmp'
)
CORS(app)

# Use environment variable for MongoDB URI
MONGODB_URI = os.environ.get("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("MONGODB_URI environment variable not set. Please set it to your MongoDB connection string.")
client = MongoClient(MONGODB_URI)
db = client["test"]
collection = db["video_metadata"]

@app.route('/')
def home():
    return render_template('landing.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/generated_vid')
def generated_vid():
    return render_template('videotrim.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/get_metadata', methods=["POST"])
def get_metadata():
    data = request.json
    if not data or 'filename' not in data:
        return jsonify({'error': 'Filename is required'}), 400
    filename = data['filename']
    name_without_extension = os.path.splitext(filename)[0]
    result = collection.find_one({"clip_name": name_without_extension})
    if not result:
        return jsonify({'error': 'No metadata found for the provided filename'}), 404
    video_metadata = result.get("video_metadata", {})
    title = video_metadata.get("title", "")
    description = video_metadata.get("description", "")
    tags = video_metadata.get("tags", [])
    return jsonify({
        "title": title,
        "description": description,
        "tags": tags
    }), 200


# --- Model Integration Endpoint ---
import subprocess
import sys

@app.route('/generate_shorts', methods=['POST'])
def generate_shorts():
    """
    Accepts JSON with youtube_url, top_n, and time_range, and runs model/master.py as if from CLI.
    """
    data = request.json
    if not isinstance(data, dict):
        return jsonify({'error': 'Invalid JSON body'}), 400
    youtube_url = data.get('youtube_url')
    top_n = data.get('top_n', 5)
    time_range = data.get('time_range', 15)
    if not youtube_url:
        return jsonify({'error': 'youtube_url is required'}), 400
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'model', 'master.py')
        # Simulate CLI input by passing arguments via subprocess and feeding input()
        # master.py expects input() for url, top_n, time_range, so we pass them via stdin
        input_str = f"{youtube_url}\n{top_n}\n{time_range}\n"
        result = subprocess.run(
            [sys.executable, script_path],
            input=input_str,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return jsonify({'output': result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f"Model script failed: {e.stderr}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Model Integration Endpoint ---
# (Deprecated: use /generate_shorts instead)
@app.route('/generate', methods=['POST'])
def generate_output():
    """
    (Deprecated) Runs model/master.py and returns its output as JSON.
    """
    try:
        script_path = os.path.join(os.path.dirname(__file__), 'model', 'master.py')
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
        return jsonify({'output': result.stdout})
    except subprocess.CalledProcessError as e:
        return jsonify({'error': f"Model script failed: {e.stderr}"}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000)