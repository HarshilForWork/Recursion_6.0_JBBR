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

