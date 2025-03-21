from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
import shutil
import time
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from oauth2client.service_account import ServiceAccountCredentials
import cloudinary
import cloudinary.uploader

app = Flask(__name__)

# 🔹 הגדרות נתיבים
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 🔹 חיבור ל-Google Drive (חייבים קובץ JSON של הרשאות API)
SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = 'service_account.json'  # הכנס כאן את קובץ ההרשאות שלך

def drive_auth():
    credentials = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, SCOPES)
    return build('drive', 'v3', credentials=credentials)

# 🔹 הגדרות Cloudinary
cloudinary.config(
    cloud_name="YOUR_CLOUD_NAME",
    api_key="YOUR_API_KEY",
    api_secret="YOUR_API_SECRET"
)

@app.route('/split-audio', methods=['POST'])
def split_audio():
    # 🔹 קבלת קובץ מהבקשה
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    filename = file.filename
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # 🔹 ניקוי קבצים ישנים
    clean_old_files()

    # 🔹 יצירת קבצים מחולקים
    output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")
    command = f"ffmpeg -i '{filepath}' -f segment -segment_time 600 -c copy '{output_pattern}'"
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFMPEG failed: {e}"}), 500

    # 🔹 שליחת הקבצים ל-Google Drive
    drive_service = drive_auth()
    parts = []
    for part in os.listdir(OUTPUT_FOLDER):
        if part.endswith(".mp3"):
            part_path = os.path.join(OUTPUT_FOLDER, part)
            drive_link = upload_to_drive(drive_service, part_path)
            cloudinary_link = upload_to_cloudinary(part_path)
            parts.append({"file": part, "drive_link": drive_link, "cloudinary_link": cloudinary_link})

    return jsonify({"parts": parts})

@app.route('/files/<path:filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

def clean_old_files():
    now = time.time()
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            if os.stat(file_path).st_mtime < now - 3600:  # מוחק קבצים ישנים יותר משעה
                os.remove(file_path)

def upload_to_drive(service, file_path):
    file_metadata = {'name': os.path.basename(file_path)}
    media = MediaFileUpload(file_path, mimetype='audio/mpeg')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return f"https://drive.google.com/uc?id={file.get('id')}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
