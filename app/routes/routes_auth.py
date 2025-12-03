from flask import Blueprint, jsonify, request
from app.services import auth_service
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.decorators import super_admin_required  # Importe o novo decorator
from app.extensions import limiter

bp_auth = Blueprint('auth', __name__)


# --- ROTAS PÚBLICAS ---

@bp_auth.route('/register', methods=['POST'])
@limiter.limit("5 per day")
def register():
    data = request.get_json()
    try:
        # Pega dados opcionais com .get() para evitar erro se não vierem
        new_user = auth_service.register_user(
            name=data['name'],
            email=data['email'],
            password=data['password'],
            whatsapp=data.get('whatsapp'),
            street=data.get('street'),
            number=data.get('number'),
            neighborhood=data.get('neighborhood'),
            complement=data.get('complement')
        )
        return jsonify({'message': 'Cliente criado com sucesso!'}), 201
    except ValueError as e:
        return jsonify({'message': str(e)}), 400


@bp_auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    result = auth_service.login_user(data['email'], data['password'])

    if result:
        return jsonify({'message': 'Bem-vindo!', **result}), 200

    return jsonify({'message': 'Credenciais inválidas'}), 401


# app/routes/routes_auth.py

# ... (outras rotas) ...

@bp_auth.route('/update', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    data = request.get_json()

    try:
        updated_user = auth_service.update_user_info(user_id, data)
        return jsonify({'message': 'Perfil atualizado!', 'user': updated_user}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

# --- ROTA SECRETA (NÍVEL DEUS) ---

@bp_auth.route('/admin/create', methods=['POST'])
@super_admin_required()  # <--- O segredo está aqui. Só você passa.
def create_restaurant_admin():
    """
    Rota para criar gerentes do restaurante.
    JSON: { "name": "Gerente 1", "email": "gerente@loja.com", "password": "123" }
    """
    data = request.get_json()
    actor_id = get_jwt_identity()  # Seu ID

    try:
        new_admin = auth_service.create_admin_by_super(actor_id, data)
        return jsonify({
            'message': 'Novo Admin de Restaurante criado!',
            'admin': {'email': new_admin.email, 'role': new_admin.role}
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400