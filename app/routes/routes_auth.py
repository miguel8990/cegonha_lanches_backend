from flask import Blueprint, jsonify, request, redirect, make_response
from app.services import auth_service
from flask_jwt_extended import jwt_required, get_jwt_identity, unset_jwt_cookies
from app.decorators import super_admin_required  # Importe o novo decorator
from app.extensions import limiter
from flask_jwt_extended import get_jwt, set_access_cookies
from app.models import User, db


import os


bp_auth = Blueprint('auth', __name__)


# --- ROTAS PÚBLICAS ---

@bp_auth.route('/register', methods=['POST'])
@limiter.limit("5 per day")
def register():
    data = request.get_json()

    # registro = register_user(data) <-- ANTIGO (chamava direto a função local ou importada incorretamente)
    registro = auth_service.register_user(data)  # NOVO: Chama do serviço

    # Cria usuário, mas NÃO verificado
    if registro['sucesso']:
        return jsonify(registro), 201
    else:
        msg_erro = registro.get('erro', 'Erro desconhecido')
        return jsonify({"error": msg_erro}), 400


@bp_auth.route('/login', methods=['POST'])
@limiter.limit("8 per hour")
def login():
    data = request.get_json()

    # resultado = login_user(data) <-- ANTIGO
    resultado = auth_service.login_user(data)  # NOVO

    if not resultado.get('sucesso'):
        return jsonify(resultado), 401

    # 2. Gera o token
    # access_token = create_token(resultado["user"]["id"]) <-- ANTIGO (acessava ID como int)

    # NOVO: Garante que é string e usa função do service se quiser, ou local.
    # Como auth_service tem create_token, usamos ela.
    access_token = auth_service.create_token(resultado["user"]["id"])

    # 3. Cria a resposta JSON (SÓ com os dados do usuário, SEM o token visível)
    resp = jsonify({
        "user": resultado['user'],  # O service já devolve o objeto serializavel ou dict
        "message": "Login realizado com sucesso",
        "token": access_token

    })

    # 4. A Mágica: Coloca o token no Cookie seguro
    set_access_cookies(resp, access_token)

    return resp, 200


@bp_auth.route('/confirm-email', methods=['GET'])
@limiter.limit("5 per hour")
def confirm_email():
    token = request.args.get('token')
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8000')

    # resultado = confirmar_email(token) <-- ANTIGO
    resultado = auth_service.confirmar_email(token)  # NOVO

    if resultado["sucesso"]:
        dest_url = f"{frontend_url}/index.html?status=verified"
        resp = make_response(redirect(dest_url))

        set_access_cookies(resp, resultado['token'])
        return resp  # Adicionado return resp que faltava no original para efetivar o cookie
    else:
        return redirect(f"{frontend_url}/index.html?status=error_token")


# app/routes/routes_auth.py

@bp_auth.route('/magic-login/request', methods=['POST', 'OPTIONS'])
@limiter.limit("8 per hour")
def request_magic_link():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'}), 200

    data = request.get_json()


    # --- NOVO CÓDIGO (Chamando o Service) ---
    resultado = auth_service.magic_link(data)

    if resultado['sucesso']:
        return jsonify({'message': resultado['mensagem']}), 200
    else:
        return jsonify({'error': resultado['erro']}), 400


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
@super_admin_required()
@limiter.limit("5 per hour")  # <--- O segredo está aqui. Só você passa.
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
@limiter.limit("6 per day")
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


@bp_auth.route('/admin/dados', methods=['GET'])
@super_admin_required()
def pegar_dados_admin():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    # Verifica se usuário existe e é admin
    if not user or user.role != 'super_admin':
        return jsonify({'message': 'Acesso proibido!'}), 403

    # Define os dados que faltavam no código anterior
    dados_secretos = {
        "status": "Acesso Permitido",
        "info": "Área restrita do Super Admin acessada com sucesso."
    }

    return jsonify(dados_secretos), 200


# app/routes/routes_auth.py

@bp_auth.route('/magic-login/confirm', methods=['GET'])
@limiter.limit("10 per day")
def confirm_magic_link():
    token = request.args.get('token')
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8000')


    # --- NOVO CÓDIGO (Usando o Service) ---
    # Usamos confirmar_email do service porque você atualizou ele para aceitar magic_link_login também!
    resultado = auth_service.confirmar_email(token)

    if resultado["sucesso"]:
        dest_url = f"{frontend_url}/index.html?status=verified&token={resultado['token']}&name={resultado['name']}&role={resultado['role']}&id={resultado['id']}&whatsapp={resultado['whatsapp']}"
        resp = make_response(redirect(dest_url))

        # Agora o Cookie é setado corretamente (antes estava apenas na URL)
        set_access_cookies(resp, resultado['token'])
        return resp
    else:
        return redirect(f"{frontend_url}/index.html?status=error_token")


# app/routes/routes_auth.py

# app/routes/routes_auth.py

# app/routes/routes_auth.py

@bp_auth.route('/google', methods=['POST'])
@limiter.limit("8 per hour")
def google_auth():
    data = request.get_json()
    credential_token = data.get('credential')

    if not credential_token:
        return jsonify({'message': 'Credencial inválida.'}), 400

    try:
        # 1. Autentica e recebe o objeto USER
        user = auth_service.login_with_google(credential_token)
        session_token = auth_service.create_token(user.id)

        # 2. Prepara os dados de resposta (JSON)
        # Inclui o TOKEN explicitamente para o celular salvar
        resp_data = {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "whatsapp": user.whatsapp
            }
        }

        # 3. Cria a resposta UMA ÚNICA VEZ
        response = jsonify(resp_data)

        # 4. Configura o Cookie (Backup para Desktop)

        set_access_cookies(response, session_token)

        return response, 200

    except ValueError as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        print(f"Erro Google Login: {e}")
        return jsonify({'message': 'Erro interno no login Google'}), 500


@bp_auth.route('/logout', methods=['POST'])
def logout():
    response = jsonify({"msg": "Logout com sucesso"})
    # Apaga o cookie definindo validade para o passado
    unset_jwt_cookies(response)
    return response



@bp_auth.route('/me', methods=['GET'])
@jwt_required() # <--- ESSENCIAL: Protege a rota com o cookie HttpOnly
def get_user_data():
    """
    Retorna os dados públicos do usuário logado (usado pelo frontend para a UI).
    """
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)

    if not user:
        # Se por algum motivo o ID do token não existir no banco
        return jsonify({"msg": "Usuário não encontrado"}), 404

    # Retorna apenas os dados necessários para a interface (sem a hash da senha)
    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "whatsapp": user.whatsapp,
        "is_verified": user.is_verified
    }), 200