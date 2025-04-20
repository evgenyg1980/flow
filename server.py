import os
import re
import uuid
import subprocess
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def clear_output_folder():
    for f in os.listdir(OUTPUT_FOLDER):
        file_path = os.path.join(OUTPUT_FOLDER, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

@app.route('/split-audio', methods=['POST'])
def split_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    clear_output_folder()

    # Optional: Create per-session folder if needed
    # session_id = str(uuid.uuid4())
    # session_output = os.path.join(OUTPUT_FOLDER, session_id)
    # os.makedirs(session_output, exist_ok=True)
    # output_pattern = os.path.join(session_output, "part_%03d.mp3")

    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

    # Properly re-encode to MP3
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

    try:
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "FFMPEG failed",
            "details": e.stderr.decode()
        }), 500

    # Get list of parts and sort
    parts = sorted(
        [f"/download/{f}" for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")],
        key=lambda x: int(re.search(r"part_(\d+)", x).group(1))
    )

    return jsonify({"parts": parts})

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
