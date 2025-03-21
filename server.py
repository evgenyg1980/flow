import os
import re
import subprocess
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/split-audio', methods=['POST'])
def split_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    file.save(filepath)

    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")
    command = f"ffmpeg -i '{filepath}' -f segment -segment_time 600 -c copy '{output_pattern}'"

    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError:
        return jsonify({"error": "FFMPEG failed"}), 500

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
