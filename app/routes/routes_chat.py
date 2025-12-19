from flask import Blueprint, jsonify, request
from app.services import chat_service
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.decorators import admin_required

bp_chat = Blueprint('chat', __name__)


# --- ROTA CLIENTE ---

@bp_chat.route('', methods=['GET'])
@jwt_required()
def get_my_messages():
    user_id = get_jwt_identity()
    msgs = chat_service.get_user_messages_logic(user_id)
    return jsonify(msgs), 200


@bp_chat.route('', methods=['POST'])
@jwt_required()
def send_message():
    user_id = get_jwt_identity()
    data = request.get_json() 
    try:
        msg = chat_service.send_message_logic(user_id, data.get('message'), is_admin=False)
        return jsonify(msg), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# --- ROTA ADMIN (Para o restaurante responder depois) ---
# O admin precisa passar o ?user_id=ID_DO_CLIENTE na URL
@bp_chat.route('/admin/reply', methods=['POST'])
@admin_required()
def admin_reply():
    data = request.get_json()
    target_user_id = data.get('user_id')  # ID do cliente que vai receber
    text = data.get('message')

    try:
        msg = chat_service.send_message_logic(target_user_id, text, is_admin=True)
        return jsonify(msg), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ... (imports anteriores) ...

# ROTA ADMIN: Listar Conversas
@bp_chat.route('/admin/conversations', methods=['GET'])
@admin_required()
def list_conversations():
    try:
        summary = chat_service.get_conversations_summary_logic()
        return jsonify(summary), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ROTA ADMIN: Ver histórico de UM cliente
@bp_chat.route('/admin/history/<int:target_user_id>', methods=['GET'])
@admin_required()
def get_user_history(target_user_id):
    try:
        msgs = chat_service.get_admin_chat_history_logic(target_user_id)
        return jsonify(msgs), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400