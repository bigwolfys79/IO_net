from flask import Flask, request, jsonify
from flask import send_from_directory
import os
import logging
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
# from logging_config import configure_logging

# # Вызываем configure_logging() в начале
# configure_logging()
# # Получаем логгер для сервера
# logging = logging.getLogger('server')
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename):
    """Checking if the file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/health", methods=["GET"])
def health_check():
    """Returning a simple health check endpoint."""
    return jsonify({"status": "healthy"}), 200

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handling file upload to the server."""
    if "image" not in request.files:
        return jsonify({"error": "No image part"}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        shareable_link = f"http://localhost:5000/uploads/{filename}"
        return jsonify({"image_id": filename, "link": shareable_link}), 200
    return jsonify({"error": "Unsupported file type"}), 400

@app.route("/delete/<image_id>", methods=["DELETE"])
def delete_file(image_id):
    """Deleting a file from the server."""
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], image_id)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"message": "File deleted"}), 200
    return jsonify({"error": "File not found"}), 404

@app.route("/uploads/<filename>", methods=["GET"])
def serve_file(filename):
    """Serving uploaded files."""
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(host="0.0.0.0", port=5000, debug=True)