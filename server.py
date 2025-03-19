from flask import Flask, request, jsonify
import os
import subprocess

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
    
    # חיתוך הקובץ ל-10 דקות (600 שניות) לכל חלק
    command = f"ffmpeg -i {filepath} -f segment -segment_time 600 -c copy {output_pattern}"
    subprocess.run(command, shell=True)

    # יצירת רשימה של קבצים שנוצרו
    parts = [f"/output/{f}" for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]

    return jsonify({"parts": parts})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
