import os
import uuid
import subprocess
import threading
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
STATUS_FILE = "status.txt"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def clear_output_folder():
    for f in os.listdir(OUTPUT_FOLDER):
        file_path = os.path.join(OUTPUT_FOLDER, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

def convert_to_mp3(input_path):
    output_path = input_path.rsplit('.', 1)[0] + ".mp3"
    command = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-acodec", "libmp3lame",
        output_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise Exception("FFmpeg conversion failed")
    return output_path

def split_audio_background(filepath, output_pattern, meeting_id):
    with open(STATUS_FILE, "w") as f:
        f.write("processing")

    try:
        mp3_path = convert_to_mp3(filepath)
    except Exception:
        with open(STATUS_FILE, "w") as f:
            f.write("error: conversion failed")
        return

    command = [
        "ffmpeg",
        "-i", mp3_path,
        "-f", "segment",
        "-segment_time", "600",
        "-c:a", "libmp3lame",
        "-ar", "44100",
        "-ac", "2",
        output_pattern
    ]
    subprocess.run(command)

    with open(STATUS_FILE, "w") as f:
        f.write("done")

    with open("meeting_id.txt", "w") as f:
        f.write(meeting_id)

@app.route('/split-audio', methods=['POST'])
def split_audio():
    if 'file' not in request.files or 'meeting_id' not in request.form:
        return jsonify({"error": "Missing file or meeting_id"}), 400

    file = request.files['file']
    meeting_id = request.form['meeting_id']

    ext = os.path.splitext(file.filename)[-1].lower()
    filename = f"{uuid.uuid4().hex}{ext if ext else '.mp3'}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    clear_output_folder()

    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

    thread = threading.Thread(target=split_audio_background, args=(filepath, output_pattern, meeting_id))
    thread.start()

    return jsonify({"message": "Splitting started"}), 202

@app.route('/split-status', methods=['GET'])
def split_status():
    if not os.path.exists(STATUS_FILE):
        return jsonify({"status": "no process started"}), 404

    with open(STATUS_FILE, "r") as f:
        status = f.read().strip()

    meeting_id = "unknown"
    if os.path.exists("meeting_id.txt"):
        with open("meeting_id.txt", "r") as f:
            meeting_id = f.read().strip()

    parts = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]

    return jsonify({
        "status": status,
        "meeting_id": meeting_id,
        "parts": parts
    }), 200

@app.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(OUTPUT_FOLDER, filename)
    if not os.path.isfile(file_path):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
