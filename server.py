from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
import glob

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

# יצירת תיקיות אם הן לא קיימות
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# פונקציה לניקוי קבצים ישנים (סעיף 3)
def clean_old_files():
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        files = glob.glob(f"{folder}/*")
        for f in files:
            os.remove(f)

@app.route('/split-audio', methods=['POST'])
def split_audio():
    """ מקבל קובץ שמע, ממיר אותו (אם צריך) ומחלק אותו לקטעים """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    # ניקוי קבצים ישנים לפני יצירה חדשה
    clean_old_files()

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(os.getcwd(), UPLOAD_FOLDER, filename)
    file.save(filepath)

    # המרה ל-MP3 אם צריך
    if not filename.endswith('.mp3'):
        new_filepath = filepath.replace(os.path.splitext(filepath)[1], ".mp3")
        convert_command = f"ffmpeg -i {filepath} {new_filepath}"
        subprocess.run(convert_command, shell=True)
        filepath = new_filepath  

    # יצירת נתיב פלט
    output_pattern = os.path.join(os.getcwd(), OUTPUT_FOLDER, "part_%03d.mp3")

    # חיתוך הקובץ לקטעים של 10 דקות (600 שניות)
    command = f"ffmpeg -y -i {filepath} -f segment -segment_time 600 -c copy {output_pattern}"
    subprocess.run(command, shell=True)

    # רשימת הקבצים שנוצרו
    parts = [f"/output/{f}" for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]

    return jsonify({"message": "File split successfully", "parts": parts})

@app.route('/get-audio/<filename>', methods=['GET'])
def get_audio(filename):
    """ מאפשר הורדת קובץ שמע מחולק (סעיף 2) """
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
