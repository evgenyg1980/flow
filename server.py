import os
import uuid
import subprocess
import threading
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
STATUS_FILE = "status.txt"

WEBHOOK_URL = "https://hook.eu2.make.com/undkzgf3l8jry9jhw2ri2w2t6f52q6g6"  # <- החלף לכתובת שלך

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

    # כתיבת סטטוס סיום
    with open(STATUS_FILE, "w") as f:
        f.write(f"done|{meeting_id}")

    # שליחת הודעה ל-Make Webhook
    try:
        res = requests.post(WEBHOOK_URL, json={"meeting_id": meeting_id})
        res.raise_for_status()
        print("[INFO] Callback sent to Make webhook.")
    except Exception as e:
        print("[ERROR] Failed to send webhook to Make:", e)

@app.route('/split-audio', methods=['POST'])
def split_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    meeting_id = request.form.get("meeting_id")
    print("[LOG] Received meeting_id:", meeting_id)

    clear_output_folder()
    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

    # Start background thread for splitting
    thread = threading.Thread(target=split_audio_background, args=(filepath, output_pattern, meeting_id))
    thread.start()

    return jsonify({"message": "Splitting started"}), 202

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
