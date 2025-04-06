from flask import Flask, request, jsonify, send_from_directory
import os
import sys
import uuid
from werkzeug.utils import secure_filename
import requests
from flask_cors import cross_origin

app = Flask(__name__)

UPLOAD_FOLDER = '/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def authenticate_request():
    token = request.args.get('access_token') or request.headers.get('Access-Token')
    
    # For now, assume that if a token is present, the request is authenticated.
    return token is not None

@app.route("/upload", methods=["POST"])
@cross_origin()
def upload_file():
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Append a unique ID to prevent collisions
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # log file upload
        print(f"File uploaded: {file_path}", file=sys.stderr)
        return jsonify({"filename": unique_filename}), 201
    else:
        return jsonify({"error": "File type not allowed"}), 400

@app.route("/files/<filename>", methods=["GET"])
def get_file(filename):

    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=80)