from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess

app = Flask(__name__)

# תיקיות לקבצים
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

# יצירת תיקיות אם הן לא קיימות
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ✅ בדיקות תקינות
print("📂 Checking directory structure...")
print("Uploads folder exists:", os.path.exists(UPLOAD_FOLDER))
print("Output folder exists:", os.path.exists(OUTPUT_FOLDER))
print("📂 Current files in root directory:", os.listdir("."))


@app.route('/split-audio', methods=['POST'])
def split_audio():
    # בדיקה אם קובץ נשלח
    if 'file' not in request.files:
        print("🚨 No file provided in request")
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # שמירת הקובץ
    file.save(filepath)
    print(f"✅ File saved at: {filepath}")

    # ✅ הדפסת קבצים בתיקיית uploads
    print("📂 Files in uploads directory:", os.listdir(UPLOAD_FOLDER))

    # בדיקה אם הקובץ באמת נשמר
    if not os.path.exists(filepath):
        print("🚨 ERROR: File was not saved correctly!")
        return jsonify({"error": "File save failed"}), 500

    # הגדרת שם הקבצים המפוצלים
    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

    # 🔄 יצירת פקודה לפיצול קובץ האודיו
    command = f"ffmpeg -i '{filepath}' -f segment -segment_time 600 -c copy '{output_pattern}'"

    # ✅ הדפסת הפקודה לפני ביצוע
    print(f"🔄 Running command: {command}")

    try:
        subprocess.run(command, shell=True, check=True)
        print("✅ FFMPEG executed successfully")
    except subprocess.CalledProcessError as e:
        print(f"🚨 FFMPEG ERROR: {e}")
        return jsonify({"error": "FFMPEG failed"}), 500

    # ✅ הדפסת הקבצים שנוצרו
    parts = [f"/output/{f}" for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]
    print("📂 Split files:", parts)

    return jsonify({"parts": parts})


# ✅ נתיב לגישה ישירה לקבצים המחולקים
@app.route('/output/<filename>')
def get_audio(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
