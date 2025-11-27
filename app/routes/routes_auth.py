from flask import Blueprint, jsonify, request
from app.services import auth_service

bp_auth = Blueprint('auth', __name__)


@bp_auth.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    try:
        # Chama o serviço para tentar registrar
        new_user = auth_service.register_user(
            name=data['name'],
            email=data['email'],
            password=data['password']
        )
        return jsonify({'message': 'Usuário criado com sucesso!'}), 201

    except ValueError as e:
        # Se o serviço reclamar (ex: email duplicado), devolvemos erro 400
        return jsonify({'message': str(e)}), 400


@bp_auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Chama o serviço de login
    result = auth_service.login_user(data['email'], data['password'])

    if result:
        return jsonify({'message': 'Login realizado!', **result}), 200

    return jsonify({'message': 'Email ou senha inválidos'}), 401