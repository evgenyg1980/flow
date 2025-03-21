from flask import Flask, request, jsonify
import os
import subprocess

app = Flask(__name__)

# נתיבי תיקיות
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

# יצירת התיקיות אם הן לא קיימות
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ✅ הדפסת בדיקה שהתיקיות קיימות
print("📂 Checking directory structure...")
print("Uploads folder exists:", os.path.exists(UPLOAD_FOLDER))
print("Output folder exists:", os.path.exists(OUTPUT_FOLDER))
print("📂 Current files in root directory:", os.listdir("."))


@app.route('/split-audio', methods=['POST'])
def split_audio():
    # בדיקה אם הקובץ נשלח בבקשה
    if 'file' not in request.files:
        print("🚨 No file provided in request")
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # שמירת הקובץ
    file.save(filepath)
    print(f"✅ File saved at: {filepath}")

    # ✅ הדפסת הקבצים שבתיקיית uploads
    print("📂 Files in uploads directory:", os.listdir(UPLOAD_FOLDER))

    # אם הקובץ לא נשמר, נזרוק שגיאה
    if not os.path.exists(filepath):
        print("🚨 ERROR: File was not saved correctly!")
        return jsonify({"error": "File save failed"}), 500

    # הגדרת תבנית הפלט של החלקים
    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

    # 🔄 בניית הפקודה לפיצול קובץ
    command = f"ffmpeg -i '{filepath}' -f segment -segment_time 600 -c copy '{output_pattern}'"
    
    # ✅ הדפסת הפקודה לפני הרצה
    print(f"🔄 Running command: {command}")

    try:
        subprocess.run(command, shell=True, check=True)
        print("✅ FFMPEG executed successfully")
    except subprocess.CalledProcessError as e:
        print(f"🚨 FFMPEG ERROR: {e}")
        return jsonify({"error": "FFMPEG failed"}), 500

    # ✅ הדפסת הקבצים שנוצרו לאחר הפיצול
    parts = [f"{OUTPUT_FOLDER}/{f}" for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]
    print("📂 Split files:", parts)

    return jsonify({"parts": parts})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
