import os
from flask import Blueprint, request, jsonify
from app.decorators import admin_required
import cloudinary
import cloudinary.uploader
import cloudinary.api

bp_upload = Blueprint('upload', __name__)

# Configuração (Lê do .env)
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # Aumentei para 5MB para ser mais permissivo


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

    # Validação de Tamanho
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    if file_size > MAX_FILE_SIZE:
        return jsonify({'error': 'Arquivo muito grande! Máximo permitido: 5MB'}), 413

    if file and allowed_file(file.filename):
        try:
            # Upload simples para a raiz (sem folder, sem tags)
            upload_result = cloudinary.uploader.upload(file, resource_type="image")

            return jsonify({
                'message': 'Upload realizado!',
                'url': upload_result['secure_url'],
                'public_id': upload_result['public_id']  # Retornamos o ID para uso futuro
            }), 201

        except Exception as e:
            return jsonify({'error': f'Erro no Cloudinary: {str(e)}'}), 500

    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400


@bp_upload.route('/gallery', methods=['GET'])
@admin_required()
def list_cloud_gallery():
    try:
        # Busca TODAS as imagens da conta (sem filtro de pasta ou tag)
        result = cloudinary.api.resources(
            type="upload",
            max_results=100,  # Traz as 100 mais recentes
            direction="desc"
        )

        images = []
        for resource in result.get('resources', []):
            images.append({
                'url': resource['secure_url'],
                'name': resource['public_id']  # O ID é necessário para deletar
            })

        return jsonify(images), 200
    except Exception as e:
        print(f"❌ Erro Galeria: {str(e)}")
        return jsonify({'error': str(e)}), 500


# --- NOVA ROTA DE DELETAR ---
@bp_upload.route('/gallery', methods=['DELETE'])
@admin_required()
def delete_image():
    data = request.get_json()
    public_id = data.get('public_id')

    if not public_id:
        return jsonify({'error': 'ID da imagem não informado'}), 400

    try:
        # Apaga do Cloudinary
        result = cloudinary.uploader.destroy(public_id)

        if result.get('result') == 'ok':
            return jsonify({'message': 'Imagem apagada com sucesso'}), 200
        else:
            return jsonify({'error': 'Erro ao apagar imagem'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500