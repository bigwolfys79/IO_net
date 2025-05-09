from flask import Flask, request, jsonify
from flask import send_from_directory
import os
import logging
from werkzeug.utils import secure_filename
from config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from logging_config import configure_logging

# Настраиваем логирование
configure_logging()
server_logger = logging.getLogger('server')

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    """Checking if the file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/health", methods=["GET"])
def health_check():
    """Returning a simple health check endpoint."""
    server_logger.debug("Health check endpoint accessed")
    return jsonify({"status": "healthy"}), 200

@app.route("/upload", methods=["POST"])
def upload_file():
    """Handling file upload to the server."""
    server_logger.debug("Upload endpoint accessed")
    if "image" not in request.files:
        server_logger.error("No image part in upload request")
        return jsonify({"error": "No image part"}), 400
    file = request.files["image"]
    if file.filename == "":
        server_logger.error("No selected file in upload request")
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)
        shareable_link = f"http://localhost:5000/uploads/{filename}"
        server_logger.info(f"File uploaded: {filename}, saved at {file_path}")
        return jsonify({"image_id": filename, "link": shareable_link}), 200
    server_logger.error(f"Unsupported file type: {file.filename}")
    return jsonify({"error": "Unsupported file type"}), 400

@app.route("/delete/<image_id>", methods=["DELETE"])
def delete_file(image_id):
    """Deleting a file from the server."""
    server_logger.debug(f"Delete endpoint accessed for image_id: {image_id}")
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], image_id)
    if os.path.exists(file_path):
        os.remove(file_path)
        server_logger.info(f"File deleted: {image_id}")
        return jsonify({"message": "File deleted"}), 200
    server_logger.error(f"File not found for deletion: {image_id}")
    return jsonify({"error": "File not found"}), 404

@app.route("/uploads/<filename>", methods=["GET"])
def serve_file(filename):
    """Serving uploaded files."""
    server_logger.debug(f"Serve file endpoint accessed for filename: {filename}")
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(file_path):
        server_logger.info(f"Serving file: {filename}")
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    server_logger.error(f"File not found for serving: {filename}")
    return jsonify({"error": "File not found"}), 404

if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    server_logger.info("Starting Flask server on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)