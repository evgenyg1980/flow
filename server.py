from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

# יצירת התיקיות אם הן לא קיימות
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/split-audio', methods=['POST'])
def split_audio():
    # בדיקה אם קובץ התקבל בבקשה
    if 'file' not in request.files:
        print("🚨 No file provided in request")
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # שמירת הקובץ
    file.save(filepath)
    print(f"✅ File saved at: {filepath}")  # 📌 בדיקה שהקובץ נשמר

    # בדיקת תוכן התיקייה לאחר השמירה
    print("📂 Files in uploads directory:", os.listdir(UPLOAD_FOLDER))  # 📌 הצגת הקבצים

    # הגדרת נתיב הפלט עבור הקבצים החתוכים
    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

    # פקודת FFMPEG לחלוקת הקובץ (10 דקות = 600 שניות)
    command = f"ffmpeg -i {filepath} -f segment -segment_time 600 -c copy {output_pattern}"
    print(f"🔄 Running command: {command}")  # 📌 הצגת הפקודה שתופעל

    # הפעלת FFMPEG
    subprocess.run(command, shell=True)

    # רשימת החלקים שנוצרו
    parts = [f"output/{f}" for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]
    print(f"🎵 Created {len(parts)} audio parts: {parts}")  # 📌 בדיקת הפלט

    return jsonify({"parts": parts})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
