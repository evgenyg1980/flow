from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

# יצירת תקיות אם הן לא קיימות
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/split-audio', methods=['POST'])
def split_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(os.getcwd(), UPLOAD_FOLDER, filename)
    file.save(filepath)

    # בדיקה אם הקובץ הוא MP3, אם לא – ממירים אותו
    if not filename.endswith('.mp3'):
        new_filepath = filepath.replace(os.path.splitext(filepath)[1], ".mp3")
        convert_command = f"ffmpeg -i {filepath} {new_filepath}"
        subprocess.run(convert_command, shell=True)
        filepath = new_filepath  

    # יצירת נתיב פלט
    output_pattern = os.path.join(os.getcwd(), OUTPUT_FOLDER, "part_%03d.mp3")

    # הרצת פקודת FFmpeg עם חיתוך קובץ ל-10 דקות כל קטע
    command = f"ffmpeg -y -i {filepath} -f segment -segment_time 600 -c copy {output_pattern}"
    subprocess.run(command, shell=True)

    # רשימת הקבצים שנוצרו
    parts = [f"/output/{f}" for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]

    return jsonify({"parts": parts})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
