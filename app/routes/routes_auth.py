from flask import Blueprint, jsonify, request, redirect
from app.services import auth_service
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.decorators import super_admin_required  # Importe o novo decorator
from app.extensions import limiter
from flask_jwt_extended import get_jwt
from app.models import User, db
from app.services.auth_service import create_token
from app.services.email_services import send_verification_email
from flask_jwt_extended import create_access_token, decode_token
import datetime
import os


bp_auth = Blueprint('auth', __name__)


# --- ROTAS PÚBLICAS ---

@bp_auth.route('/register', methods=['POST'])
@limiter.limit("5 per day")
def register():
    data = request.get_json()

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email já cadastrado'}), 400

    # Cria usuário, mas NÃO verificado
    user = User(
        name=data['name'],
        email=data['email'],
        password=data['password'],  # O modelo deve fazer hash
        phone=data.get('phone'),
        is_verified=False
    )

    db.session.add(user)
    db.session.commit()

    # Gera token específico para verificação (expira em 24h)
    verification_token = create_access_token(
        identity=user.id,
        additional_claims={"type": "email_verification"},
        expires_delta=datetime.timedelta(hours=24)
    )

    # Envia email
    send_verification_email(user.email, user.name, verification_token)

    return jsonify({
        'message': 'Cadastro realizado! Verifique seu email para ativar a conta.',
        'require_verification': True
    }), 201


@bp_auth.route('/confirm-email', methods=['GET'])
@limiter.limit("5 per day")
def confirm_email():
    token = request.args.get('token')
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8000')

    try:
        # Decodifica o token
        decoded = decode_token(token)

        if decoded.get("type") != "email_verification":
            raise Exception("Token inválido")

        user_id = decoded["sub"]
        user = User.query.get(user_id)

        if not user:
            return redirect(f"{frontend_url}/index.html?status=error_user")

        user.is_verified = True
        db.session.commit()

        # Gera token de login real para o usuário já entrar logado
        login_token = create_token(user.id)

        # Redireciona para o Front com o token na URL (para o JS pegar e logar)
        return redirect(
            f"{frontend_url}/index.html?status=verified&token={login_token}&name={user.name}&role={user.role}")

    except Exception as e:
        print(e)
        return redirect(f"{frontend_url}/index.html?status=error_token")


@bp_auth.route('/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()

    if user and user.verify_password(data['password']):
        if not user.is_verified:
            return jsonify({'message': 'Conta não verificada. Cheque seu email.'}), 403

        token = create_token(user.id)
        return jsonify({'token': token, 'user': user.to_dict()}), 200

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


@bp_auth.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')

    # Chama o serviço (ele cuida de verificar se existe e mandar o email)
    # Retornamos sempre 200 para evitar enumeração de usuários (segurança)
    auth_service.request_password_reset(email)

    return jsonify({'message': 'Se o e-mail existir, você receberá um link em breve.'}), 200


@bp_auth.route('/reset-password', methods=['POST'])
@jwt_required()  # O Token do e-mail é um JWT válido, então isso funciona!
def reset_password_confirm():
    user_id = get_jwt_identity()
    claims = get_jwt()  # Pega os dados extras do token

    # Segurança Extra: Verifica se é mesmo um token de reset
    if claims.get("type") != "password_reset":
        return jsonify({'error': 'Token inválido para esta operação.'}), 403

    data = request.get_json()
    new_pass = data.get('new_password')

    try:
        auth_service.reset_password_with_token(user_id, new_pass)
        return jsonify({'message': 'Senha alterada com sucesso! Faça login.'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        # Pega erro de token expirado do JWT automaticamente
        return jsonify({'error': 'Link expirado ou inválido.'}), 422



@app.route('/api/admin/dados', methods=['GET'])
@jwt_required() # 1. Verifica se tem token de login
def pegar_dados_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # 2. VERIFICAÇÃO DE SEGURANÇA FINAL 👇
    if user.role != 'super_admin':
        return jsonify({'message': 'Acesso proibido!'}), 403

    # Se passar, entrega o ouro
    return jsonify(dados_secretos)