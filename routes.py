from flask import render_template, request, redirect, url_for, jsonify, session
from app import app
from pymongo import MongoClient
import os

client = MongoClient("mongodb+srv://shilankfans07:jbbr123@trimly.3hglc.mongodb.net/?retryWrites=true&w=majority&appName=trimly")
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
    video_dir = 'test' 
    full_video_dir = os.path.join(app.static_folder, video_dir)
    video_files = [f for f in os.listdir(full_video_dir) if f.endswith('.mp4')]
    videos_data = [{
        'name': f,
        'url': url_for('static', filename= video_dir + '/' + f)
    } for f in video_files]
    print(videos_data)
    return render_template('videotrim.html', videos_data=videos_data)


@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/get_metadata', methods=["POST"])
def get_metadata():
    data = request.json
    
    if not data or 'filename' not in data:
        return jsonify({'error': 'Filename is required'}), 400
    
    filename = data['filename']
    
    # Remove file extension
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

@app.route('/generate-shorts', methods=['POST'])
def generate_shorts():
    try:
        data = request.json
        
        youtube_url = data.get('youtube_url')
        seconds = data.get('seconds')
        shorts = data.get('shorts')
        
        if not youtube_url or not youtube_url.strip():
            return jsonify({'success': False, 'message': 'YouTube URL is required'})
        
        if not seconds or not shorts:
            return jsonify({'success': False, 'message': 'Both seconds and number of shorts are required'})
        
        try:
            seconds = int(seconds)
            shorts = int(shorts)
        except ValueError:
            return jsonify({'success': False, 'message': 'Seconds and shorts must be valid numbers'})
        
        print(f"Received request to generate {shorts} shorts of {seconds} seconds each from URL: {youtube_url}")
        
        collection = db["urls"]
        data = {
            "url": youtube_url,
            "seconds": seconds,
            "shorts": shorts,
        }

        result = collection.insert_one(data)
        print(f"Inserted document ID: {result.inserted_id}")

        return jsonify({
            'success': True,
            'message': 'Successfully submitted',
            'redirect_url': url_for('generated_vid', video_id='temp_id')  # Replace with actual ID from processing
        })
        
    except Exception as e:
        # Log the error
        print(f"Error in generate_shorts: {str(e)}")
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'})


