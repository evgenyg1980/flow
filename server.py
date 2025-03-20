from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

# תיקיות להעלאת קבצים ולפלט
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "API is running"}), 200

@app.route('/split-audio', methods=['POST'])
def split_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # הגדרת תבנית לפלט קבצי השמע
    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

    # שימוש ב-FFmpeg לחיתוך הקובץ לקטעים של 10 דקות (600 שניות)
    command = f"ffmpeg -i {filepath} -f segment -segment_time 600 -c copy {output_pattern}"
    subprocess.run(command, shell=True)

    # יצירת רשימה של קבצים מחולקים
    parts = [f"/output/{f}" for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]

    return jsonify({"parts": parts}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
