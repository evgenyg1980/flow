from werkzeug.utils import secure_filename  # ← שורה חשובה שהוספנו

@app.route('/split-audio', methods=['POST'])
def split_audio():
    # בדיקה אם קובץ נשלח
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # בדיקת סיומת חוקית
    allowed_extensions = ['mp3', 'wav', 'm4a']
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        return jsonify({"error": "Invalid file type. Allowed types: mp3, wav, m4a"}), 400

    # בדיקה אם meeting_id הועבר
    meeting_id = request.form.get("meeting_id")
    if not meeting_id:
        return jsonify({"error": "Missing meeting_id"}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        print(f"[INFO] Received file: {filename}")
        print(f"[INFO] Meeting ID: {meeting_id}")

        clear_output_folder()
        output_pattern = os.path.join(OUTPUT_FOLDER, "part_%03d.mp3")

        # Start background thread
        thread = threading.Thread(target=split_audio_background, args=(filepath, output_pattern, meeting_id))
        thread.start()

        return jsonify({"message": "Splitting started"}), 202

    except Exception as e:
        print(f"[ERROR] Failed to process file: {e}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500
