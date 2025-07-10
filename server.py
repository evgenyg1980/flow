from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import threading
import subprocess
import requests

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"
STATUS_FILE = "status.txt"

DEFAULT_WEBHOOK_URL = "https://hook.eu2.make.com/ni7rqt3m1xtgsb5eiqehunkg97k45jm1"

WEBHOOK_MAP = {
    "appXLoxRKrV2EDOlB": os.getenv("WEBHOOK_ORI"),
    "app9jheXQXzelcTrT": os.getenv("WEBHOOK_MARINA")
}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def clear_output_folder():
    for f in os.listdir(OUTPUT_FOLDER):
        file_path = os.path.join(OUTPUT_FOLDER, f)
        if os.path.isfile(file_path):
            os.remove(file_path)

def split_audio_background(filepath, output_pattern, meeting_id, webhook_url, base_id=None):
    try:
        print("[DEBUG] Starting ffmpeg split...")
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
        subprocess.run(command, check=True)
        print("[DEBUG] Split completed")

        parts = sorted([f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")])
        files_info = []
        for part in parts:
            part_path = os.path.join(OUTPUT_FOLDER, part)
            size = os.path.getsize(part_path)
            files_info.append({
                "file_name": part,
                "file_url": f"https://flow-audio-server.onrender.com/download/{part}",
                "size": size
            })

        with open(STATUS_FILE, "w") as f:
            f.write(f"done|{meeting_id}")
        print("[DEBUG] Status file updated")

        print(f"[DEBUG] Sending webhook to: {webhook_url} with meeting_id: {meeting_id}")
        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            json={
                "meeting_id": meeting_id,
                "base_id": base_id,
                "status": "done",
                "parts": files_info
            }
        )
        response.raise_for_status()
        print(f"[INFO] Webhook sent to Make with meeting_id: {meeting_id}")

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] ffmpeg failed: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")

@app.route('/split-audio', methods=['POST'])
def split_audio():
    print("===== [DEBUG] =====")
    print("Content-Type:", request.content_type)
    print("Headers:", dict(request.headers))
    print("Form keys:", list(request.form.keys()))
    print("Files keys:", list(request.files.keys()))
    print("===================")

    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    allowed_extensions = ['mp3', 'wav', 'm4a']
filename = secure_filename(file.filename)
request_file_type = request.form.get("file_type")

if request_file_type:
    extension = request_file_type.lower()
else:
    extension = filename.split('.')[-1].lower()



    if extension not in allowed_extensions:
        return jsonify({"error": f"Invalid file extension: .{extension}. Allowed: {allowed_extensions}"}), 400

    # שמור תמיד בשם בטוח עם הסיומת הנכונה
    saved_filename = f"1.{extension}"
    filepath = os.path.join(UPLOAD_FOLDER, saved_filename)

    meeting_id = request.form.get("meeting_id")
    base_id = request.form.get("base_id")

    webhook_url = request.form.get("webhook_url")
    if not webhook_url:
        for key in request.form:
            if "webhook_url" in key and "https://hook.eu2.make.com" in request.form[key]:
                webhook_url = request.form[key]
                break
    if not webhook_url:
        webhook_url = WEBHOOK_MAP.get(base_id, DEFAULT_WEBHOOK_URL)

    if not meeting_id:
        return jsonify({"error": "Missing meeting_id"}), 400

    try:
        file.save(filepath)

        print(f"[INFO] Received file: {saved_filename}")
        print(f"[INFO] Meeting ID: {meeting_id}")
        print(f"[INFO] Base ID: {base_id}")
        print(f"[INFO] Webhook URL: {webhook_url}")

        clear_output_folder()
        output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

        thread = threading.Thread(target=split_audio_background, args=(filepath, output_pattern, meeting_id, webhook_url, base_id))
        thread.start()

        return jsonify({"message": f"Splitting started on {saved_filename}"}), 202

    except Exception as e:
        print(f"[ERROR] Failed to process file: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500

@app.route('/split-status', methods=['GET'])
def split_status():
    if not os.path.exists(STATUS_FILE):
        return jsonify({"status": "no process started"}), 404

    with open(STATUS_FILE, "r") as f:
        content = f.read().strip()

    parts = [f for f in os.listdir(OUTPUT_FOLDER) if f.endswith(".mp3")]
    parts.sort()

    if "|" in content:
        status, meeting_id = content.split("|", 1)
    else:
        status = content
        meeting_id = None

    return jsonify({
        "status": status,
        "meeting_id": meeting_id,
        "parts": parts
    }), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
