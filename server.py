import os
import re
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

def split_audio_background(filepath, output_pattern, meeting_id):
    try:
        with open(STATUS_FILE, "w") as f:
            f.write(f"processing|{meeting_id}")

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

        parts = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]
        if parts:
            with open(STATUS_FILE, "w") as f:
                f.write(f"done|{meeting_id}")
        else:
            with open(STATUS_FILE, "w") as f:
                f.write(f"error: no parts created|{meeting_id}")

    except Exception as e:
        with open(STATUS_FILE, "w") as f:
            f.write(f"error: {str(e)}|{meeting_id}")

@app.route('/split-audio', methods=['POST'])
def split_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    meeting_id = request.form.get("meeting_id", "")

    clear_output_folder()

    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

    thread = threading.Thread(target=split_audio_background, args=(filepath, output_pattern, meeting_id))
    thread.start()

    return jsonify({"message": "Splitting started"}), 202

@app.route('/split-status', methods=['GET'])
def split_status():
    try:
        if not os.path.exists(STATUS_FILE):
            return jsonify({"status": "no process started"}), 404

        with open(STATUS_FILE, "r") as f:
            status_line = f.read().strip()

        status, meeting_id = (status_line.split("|") + [""])[:2]

        parts = []
        if status == "done":
            part_files = []
            for f in os.listdir(OUTPUT_FOLDER):
                if f.endswith(".mp3"):
                    match = re.search(r"part_(\d+)", f)
                    if match:
                        part_files.append((int(match.group(1)), f))
            parts = [f[1] for f in sorted(part_files)]

        return jsonify({"status": status, "meeting_id": meeting_id, "parts": parts}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
