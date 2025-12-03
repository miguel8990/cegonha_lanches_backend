import os
from flask import Blueprint, request, jsonify, current_app, url_for
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required
from app.decorators import admin_required
import uuid

bp_upload = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp_upload.route('', methods=['POST'])
@admin_required()
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400

    if file and allowed_file(file.filename):
        # Gera nome único para evitar conflito (ex: lanche.jpg -> a1b2-c3d4.jpg)
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"

        # Salva na pasta configurada
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        # Gera a URL pública (ex: http://localhost:5000/static/uploads/nome.jpg)
        # O 'static' é uma rota padrão do Flask
        file_url = url_for('static', filename=f'uploads/{filename}', _external=True)

        return jsonify({'message': 'Upload realizado!', 'url': file_url}), 201

    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400