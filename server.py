from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import threading
import subprocess
import requests

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
STATUS_FILE = "status.txt"
WEBHOOK_URL = "https://hook.make.com/PASTE_YOUR_WEBHOOK_URL_HERE"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def clear_output_folder():
    for f in os.listdir(OUTPUT_FOLDER):
        file_path = os.path.join(OUTPUT_FOLDER, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

def split_audio_background(filepath, output_pattern, meeting_id):
    command = [
        "ffmpeg",
        "-i", filepath,
        "-f", "segment",
        "-segment_time", "600",
        "-c:a", "libmp3lame",
        "-ar", "44100",
        "-ac", "2",
        output_pattern
    ]
    subprocess.run(command)

    with open(STATUS_FILE, "w") as f:
        f.write(f"done|{meeting_id}")

    try:
        response = requests.post(WEBHOOK_URL, json={"meeting_id": meeting_id})
        response.raise_for_status()
        print(f"[INFO] Webhook sent to Make with meeting_id: {meeting_id}")
    except Exception as e:
        print(f"[ERROR] Failed to send webhook: {e}")

@app.route('/split-audio', methods=['POST'])
def split_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    allowed_extensions = ['mp3', 'wav', 'm4a']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        return jsonify({"error": "Invalid file type. Allowed types: mp3, wav, m4a"}), 400

    meeting_id = request.form.get("meeting_id")
    if not meeting_id:
        return jsonify({"error": "Missing meeting_id"}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        print(f"[INFO] Received file: {filename}")
        print(f"[INFO] Meeting ID: {meeting_id}")

        clear_output_folder()
        output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

        thread = threading.Thread(target=split_audio_background, args=(filepath, output_pattern, meeting_id))
        thread.start()

        return jsonify({"message": "Splitting started"}), 202

    except Exception as e:
        print(f"[ERROR] Failed to process file: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/split-status', methods=['GET'])
def split_status():
    if not os.path.exists(STATUS_FILE):
        return jsonify({"status": "no process started"}), 404

    with open(STATUS_FILE, "r") as f:
        content = f.read().strip()

    parts = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]
    parts.sort()

    if "|" in content:
        status, meeting_id = content.split("|", 1)
    else:
        status = content
        meeting_id = None

    return jsonify({
        "status": status,
        "meeting_id": meeting_id,
        "parts": parts
    }), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

