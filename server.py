from flask import Flask, request, jsonify
import requests
import os
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
import threading
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
STATUS_FILE = "status.txt"
AIRTABLE_API_KEY = "YOUR_AIRTABLE_API_KEY"
AIRTABLE_BASE_ID = "app9jheXQXzelcTrT"
AIRTABLE_TABLE_NAME = "tblFAHIOjG1wLAK6T"
WEBHOOK_URL = "https://hook.eu2.make.com/undkzgf3l8jry9jhw2ri2w2t6f52q6g6"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def clear_output_folder():
    for f in os.listdir(OUTPUT_FOLDER):
        file_path = os.path.join(OUTPUT_FOLDER, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

def download_file_from_url(url, filename):
    response = requests.get(url)
    if response.status_code == 200:
        with open(filename, 'wb') as f:
            f.write(response.content)
        return True
    return False

def split_audio_background(filepath, output_pattern, meeting_id):
    try:
        print("[DEBUG] Starting ffmpeg split...")
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
        subprocess.run(command, check=True)
        print("[DEBUG] Split completed")

        with open(STATUS_FILE, "w") as f:
            f.write(f"done|{meeting_id}")

        print(f"[DEBUG] Sending webhook to: {WEBHOOK_URL} with meeting_id: {meeting_id}")
        response = requests.post(
            WEBHOOK_URL,
            headers={"Content-Type": "application/json"},
            json={"meeting_id": meeting_id}
        )
        response.raise_for_status()
        print(f"[INFO] Webhook sent to Make with meeting_id: {meeting_id}")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] ffmpeg failed: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")

@app.route("/")
def index():
    return "Server is running."

@app.route('/split-audio', methods=['POST'])
def split_audio():
    meeting_id = request.json.get("meeting_id")
    if not meeting_id:
        return jsonify({"error": "Missing meeting_id"}), 400

    airtable_url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}/{meeting_id}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}"
    }
    response = requests.get(airtable_url, headers=headers)

    if response.status_code != 200:
        return jsonify({"error": "Failed to fetch record from Airtable"}), 500

    record = response.json()
    try:
        file_url = record['fields']['קובץ ידני'][0]['url']
    except (KeyError, IndexError):
        return jsonify({"error": "File not found in Airtable record"}), 404

    filename = secure_filename(urlparse(file_url).path.split('/')[-1])
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not download_file_from_url(file_url, filepath):
        return jsonify({"error": "Failed to download audio file"}), 500

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
