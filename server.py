from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
import re

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

    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

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
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            return jsonify({"error": "FFMPEG failed", "details": stderr.decode()}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
