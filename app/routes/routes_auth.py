from flask import Blueprint, jsonify, request, redirect, make_response
from app.services import auth_service
from flask_jwt_extended import jwt_required, get_jwt_identity, unset_jwt_cookies, set_access_cookies
from app.decorators import super_admin_required
from app.extensions import limiter
from flask_jwt_extended import get_jwt
from app.models import User, db
import os

bp_auth = Blueprint('auth', __name__)


# =============================================================================
# 📝 REGISTRO (CORRIGIDO)
# =============================================================================
@bp_auth.route('/register', methods=['POST'])
@limiter.limit("5 per day")
def register():
    data = request.get_json()
    registro = auth_service.register_user(data)

    if registro['sucesso']:
        # 🔥 CORREÇÃO: Criar e setar o token imediatamente após registro
        user_id = registro.get('id')
        token = auth_service.create_token(user_id)

        resp = jsonify({
            "message": "Cadastro realizado! Verifique seu email.",
            "user": {
                "id": user_id,
                "name": data.get('name'),
                "email": data.get('email'),
                "role": "client"
            }
        })

        # 🔥 SETA O COOKIE IMEDIATAMENTE
        set_access_cookies(resp, token)
        return resp, 201
    else:
        return jsonify({"error": registro.get('erro', 'Erro desconhecido')}), 400


# =============================================================================
# 🔑 LOGIN (CORRIGIDO)
# =============================================================================
@bp_auth.route('/login', methods=['POST'])
@limiter.limit("8 per hour", error_message="Muitas tentativas.")
def login():
    data = request.get_json()
    resultado = auth_service.login_user(data)

    if not resultado.get('sucesso'):
        return jsonify({"error": resultado.get('message', 'Credenciais inválidas')}), 401

    user_data = resultado["user"]
    access_token = auth_service.create_token(user_data["id"])

    resp = jsonify({
        "user": user_data,
        "message": "Login realizado com sucesso"
    })

    set_access_cookies(resp, access_token)
    return resp, 200


# =============================================================================
# ✉️ CONFIRMAÇÃO DE EMAIL (UNIFICADA)
# =============================================================================
@bp_auth.route('/confirm-email', methods=['GET'])
@limiter.limit("10 per hour", error_message="Muitas tentativas.")
def confirm_email():
    """
    Rota que valida o token, seta o cookie e redireciona para o site.
    """
    token = request.args.get('token')
    
    # 🔥 CORREÇÃO: Detecta a URL raiz dinamicamente (Tudo em Um)
    # Isso evita redirecionar para localhost quando estiver no Render
    base_url = request.url_root.rstrip('/')
    
    # URLs de destino
    success_url = f"{base_url}/index.html?status=verified"
    error_url = f"{base_url}/index.html?status=error_token"

    if not token:
        return redirect(error_url)

    # Valida o token e cria a sessão
    resultado = auth_service.confirmar_email(token)

    if resultado["sucesso"]:
        resp = make_response(redirect(success_url))

        # 🔥 PONTO CRÍTICO: Aqui o cookie de sessão é gravado!
        set_access_cookies(resp, resultado['token'])

        return resp
    else:
        return redirect(error_url)


# =============================================================================
# 🪄 MAGIC LINK - REQUEST
# =============================================================================
@bp_auth.route('/magic-login/request', methods=['POST'])
@limiter.limit("8 per hour", error_message="Muitas tentativas.")
def request_magic_link():
    data = request.get_json()
    resultado = auth_service.magic_link(data)

    if resultado['sucesso']:
        return jsonify({'message': resultado['mensagem']}), 200
    else:
        return jsonify({'error': resultado['erro']}), 400


# =============================================================================
# 🪄 MAGIC LINK - CONFIRM (REMOVIDA - USA confirm-email)
# =============================================================================
# Não precisa mais desta rota, pois /confirm-email agora trata tudo


# =============================================================================
# 🔄 ATUALIZAR PERFIL
# =============================================================================
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


# =============================================================================
# 🔐 GOOGLE AUTH (CORRIGIDO)
# =============================================================================
@bp_auth.route('/google', methods=['POST'])
@limiter.limit("8 per hour", error_message="Muitas tentativas.")
def google_auth():
    data = request.get_json()
    credential_token = data.get('credential')

    if not credential_token:
        print("credencial invalida")
        return jsonify({'message': 'Credencial inválida.'}), 400


    try:
        user = auth_service.login_with_google(credential_token)

        print(f"DEBUG AUTH: Gerando token para User ID: {user.id} (Tipo: {type(user.id)})")
        session_token = auth_service.create_token(user.id)
        if user.id is None:
            print("Falha ao gerar ID do usuário.")
            raise ValueError("Falha ao gerar ID do usuário.")
        resp_data = {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "whatsapp": user.whatsapp
            }
        }

        response = jsonify(resp_data)

        # 🔥 SETA O COOKIE
        set_access_cookies(response, session_token)
        print("cookie setado")

        return response, 200

    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        print(f"Erro Google Login: {e}")
        return jsonify({'message': 'Erro interno no login Google'}), 500


# =============================================================================
# 🚪 LOGOUT
# =============================================================================
@bp_auth.route('/logout', methods=['POST'])
def logout():
    response = jsonify({"msg": "Logout com sucesso"})
    unset_jwt_cookies(response)
    return response


# =============================================================================
# 👤 OBTER USUÁRIO ATUAL
# =============================================================================
@bp_auth.route('/me', methods=['GET'])
@jwt_required()
def get_user_data():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({"msg": "Usuário não encontrado"}), 404

    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "whatsapp": user.whatsapp,
        "is_verified": user.is_verified
    }), 200


# =============================================================================
# 🔑 RESET DE SENHA
# =============================================================================
@bp_auth.route('/forgot-password', methods=['POST'])
@limiter.limit("6 per day", error_message="Muitas tentativas.")
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    auth_service.request_password_reset(email)
    return jsonify({'message': 'Se o e-mail existir, você receberá um link em breve.'}), 200


@bp_auth.route('/reset-password', methods=['POST'])
@jwt_required()
def reset_password_confirm():
    user_id = get_jwt_identity()
    claims = get_jwt()

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
        return jsonify({'error': 'Link expirado ou inválido.'}), 422


# =============================================================================
# 👑 ADMIN ROUTES
# =============================================================================
@bp_auth.route('/admin/create', methods=['POST'])
@super_admin_required()
@limiter.limit("5 per hour")
def create_restaurant_admin():
    data = request.get_json()
    actor_id = get_jwt_identity()

    try:
        new_admin = auth_service.create_admin_by_super(actor_id, data)
        return jsonify({
            'message': 'Novo Admin de Restaurante criado!',
            'admin': {'email': new_admin.email, 'role': new_admin.role}
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp_auth.route('/admin/dados', methods=['GET'])
@super_admin_required()
def pegar_dados_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != 'super_admin':
        return jsonify({'message': 'Acesso proibido!'}), 403

    dados_secretos = {
        "status": "Acesso Permitido",
        "info": "Área restrita do Super Admin acessada com sucesso."
    }

    return jsonify(dados_secretos), 200