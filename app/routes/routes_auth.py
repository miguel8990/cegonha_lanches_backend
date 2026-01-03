from flask import Blueprint, jsonify, request, redirect, make_response, render_template
from app.services import auth_service, config_service
from flask_jwt_extended import set_refresh_cookies, jwt_required, get_jwt_identity, unset_jwt_cookies, set_access_cookies
from app.decorators import super_admin_required, verified_user_required
from app.extensions import limiter
from flask_jwt_extended import get_jwt
from app.models import User, db


bp_auth = Blueprint('auth', __name__)


# =============================================================================
# 📝 REGISTRO (CORRIGIDO)
# =============================================================================
@bp_auth.route('/register', methods=['POST'])
@limiter.limit("10 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
def register():
    data = request.get_json()
    registro = auth_service.register_user(data)

    if registro['sucesso']:
        

        return jsonify({
            "message": "Cadastro realizado! Por favor, verifique seu email para ativar a conta.",
            "require_verification": True 
        }), 201
    else:
        return jsonify({"error": registro.get('erro', 'Erro desconhecido')}), 400


# =============================================================================
# 🔑 LOGIN (CORRIGIDO)
# =============================================================================
@bp_auth.route('/login', methods=['POST'])
@limiter.limit("20 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
def login():
    data = request.get_json()
    resultado = auth_service.login_user(data)

    if not resultado.get('sucesso'):
        return jsonify({"error": resultado.get('message', 'Credenciais inválidas')}), 401

    user_data = resultado["user"]
    if not user_data.get('is_verified'):
        return jsonify({
            "error": "Email não verificado. Verifique sua caixa de entrada.",
            "code": "email_not_verified" # Código útil para o front tratar diferente se quiser
        }), 403
    access_token = auth_service.create_token(user_data["id"])
    refresh_token = auth_service.create_refresh_token(user_data["id"])
    
    resp = jsonify({
        "user": user_data,
        "message": "Login realizado com sucesso"
    })
    set_refresh_cookies(resp, refresh_token)
    set_access_cookies(resp, access_token)
    return resp, 200

@bp_auth.route('/refresh', methods=['POST'])
@jwt_required(refresh=True) # <--- Importante: Exige o Refresh Token válido
def refresh():
    current_user_id = get_jwt_identity()
    
    # Cria APENAS um novo Access Token
    new_access_token = auth_service.create_token(current_user_id)
    
    resp = jsonify({'refresh': True})
    set_access_cookies(resp, new_access_token)
    
    return resp, 200

# =============================================================================
# ✉️ CONFIRMAÇÃO DE EMAIL (UNIFICADA)
# =============================================================================
@bp_auth.route('/confirm-email', methods=['GET'])
@limiter.limit("10 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
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
        set_refresh_cookies(resp, resultado['refresh_token'])

        return resp
    else:
        return redirect(error_url)


# =============================================================================
# 🪄 MAGIC LINK - REQUEST
# =============================================================================
@bp_auth.route('/magic-login/request', methods=['POST'])
@limiter.limit("10 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
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
@verified_user_required()
@limiter.limit("10 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
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
@limiter.limit("10 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
def google_auth():
    data = request.get_json()
    credential_token = data.get('credential')

    if not credential_token:
        return jsonify({'message': 'Credencial inválida.'}), 400

    try:
        user = auth_service.login_with_google(credential_token)

        # 1. GERA OS DOIS TOKENS
        access_token = auth_service.create_token(user.id)
        refresh_token = auth_service.create_refresh_token(user.id) # <--- Faltava isso

        resp_data = {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "whatsapp": user.whatsapp,
                "is_verified": user.is_verified
            }
        }

        response = jsonify(resp_data)

        # 2. SALVA OS DOIS COOKIES
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token) # <--- Faltava isso
        
        print(f"Login Google: Cookies Access e Refresh setados para User {user.id}")

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
@limiter.limit("30 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
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
"""
@bp_auth.route('/forgot-password', methods=['POST'])
@limiter.limit("3 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    auth_service.request_password_reset(email)
    return jsonify({'message': 'Se o e-mail existir, você receberá um link em breve.'}), 200


@bp_auth.route('/reset-password', methods=['POST'])
@jwt_required()
@limiter.limit("10 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
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
"""

# =============================================================================
# 👑 ADMIN ROUTES
# =============================================================================
@bp_auth.route('/gerente', methods=['GET'])
@jwt_required(locations=['cookies']) # OBRIGA o token estar no Cookie
def view_gerente_page():
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    # Verificação Rigorosa no Servidor
    if not user or user.role != 'super_admin':
        # Se não for autorizado, redireciona para a home IMEDIATAMENTE.
        # O HTML da página de gerente nunca é enviado para o navegador.
        return redirect('/index.html')

    # Se passou, renderiza o HTML seguro
    return render_template('gerente.html')

@bp_auth.route('/admin/create', methods=['POST'])
@super_admin_required()
@limiter.limit("5 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
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
@limiter.limit("10 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
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


@bp_auth.route('/admin/list_all_users', methods=['GET'])
@super_admin_required()
@limiter.limit("20 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
def listar_all_users():
    try:
        report_data = config_service.get_users_for_delete()
        return jsonify(report_data), 200
    except Exception as e:
        print(f"Erro relatório usuários: {e}") 
        return jsonify({'error': 'Erro ao gerar lista de usuários'}), 500


@bp_auth.route('/admin/delete_user', methods=['POST'])
@super_admin_required()
@limiter.limit("20 per hour", error_message="Muitas tentativas, tente novamente mais tarde.")
def delete_user_route(): # Renomeado para evitar conflito de nome com a função importada
    data = request.get_json()
    
    # Validação simples da entrada
    if not data or 'user_id' not in data:
        return jsonify({'error': 'O campo user_id é obrigatório.'}), 400

    target_id = data['user_id']
    
    # Chama o serviço
    resultado = auth_service.delete_user(target_id)

    if resultado['sucesso']:
        return jsonify({
            "message": resultado['mensagem']
        }), 200
    else:
        return jsonify({
            "error": resultado.get('erro', 'Erro desconhecido')
        }), 400