import re
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
import bleach
import secrets
from app.models import User, db
from flask_jwt_extended import create_access_token, decode_token
from app.services.email_services import send_verification_email, send_magic_link_email, send_reset_email


# --- FUNÇÃO AUXILIAR DE VALIDAÇÃO ---
def validate_password_strength(password):
    """
    Replica a lógica de segurança do frontend (main.js).
    Retorna (True, None) se válido ou (False, mensagem_erro).
    """
    if len(password) < 8:
        return False, "A senha deve ter no mínimo 8 caracteres."

    # Verifica Maiúscula
    if not re.search(r"[A-Z]", password):
        return False, "A senha deve conter pelo menos uma letra maiúscula."

    # Verifica Minúscula
    if not re.search(r"[a-z]", password):
        return False, "A senha deve conter pelo menos uma letra minúscula."

    # Verifica Número
    if not re.search(r"[0-9]", password):
        return False, "A senha deve conter pelo menos um número."

    # Verifica Caractere Especial
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "A senha deve conter pelo menos um caractere especial (!@#...)."

    return True, None


def create_token(user_id):
    """
    Gera um token de acesso padrão para o usuário.
    Centraliza a criação de tokens para ser usada no login e na confirmação de email.
    """
    return create_access_token(identity=str(user_id))


def register_user(dados):
    """
    Registro Público (App do Cliente).
    Sempre cria com role='client'.
    """
    raw_nome = dados.get('name', '')
    raw_email = dados.get('email', '')
    nome = bleach.clean(raw_nome, tags=[], strip=True).strip()
    email = bleach.clean(raw_email, tags=[], strip=True).strip().lower()
    senha = dados.get('password')
    whatsapp = dados.get('whatsapp') or ''

    raw_whatsapp = dados.get('whatsapp') or ''
    if len(whatsapp) > 20:
        return {"sucesso": False, "erro": "Número de WhatsApp inválido ou muito longo."}
        # Remove tudo que não for dígito do whatsapp para salvar apenas números
    else:
        whatsapp = ''.join(char for char in str(raw_whatsapp) if char.isdigit())
        if len(whatsapp) not in [10, 11]:
            return {
                "sucesso": False,
                "erro": f"WhatsApp inválido. O número deve ter 10 ou 11 dígitos (DDD + Número). Você enviou {len(whatsapp)}."
            }
    if len(email) > 255:
        return {"sucesso": False, "erro": "e-mail inválido ou muito longo."}
    if len(nome) > 150:
        return {"sucesso": False, "erro": "Nome muito longo."}
    if len(senha) > 140:
        return {"sucesso": False, "erro": "Senha muito longa."}


    if not nome or not email or not senha:
        return {"sucesso": False, "erro": "Todos os campos obrigatórios devem ser preenchidos."}

    # 1. Validação de Email Duplicado
    if User.query.filter_by(email=email).first():
        return {"sucesso": False, "erro": "Este email já está cadastrado."}

    # 2. [NOVO] Validação de Força de Senha
    is_valid, error_msg = validate_password_strength(senha)
    if not is_valid:
        return {"sucesso": False, "erro": error_msg}

    hashed_password = generate_password_hash(senha)

    new_user = User(
        name=nome,
        email=email,
        password_hash=hashed_password,
        role='client',  # Força nível baixo
        whatsapp=whatsapp
    )
    try:
        db.session.add(new_user)
        db.session.commit()
        db.session.refresh(new_user)
    except Exception as e:
        db.session.rollback()
        return {"sucesso": False, "erro": f"Erro no banco de dados: {str(e)}"}

    # Gera token para email_verification (24h de validade)
    verification_token = create_access_token(
        identity=str(new_user.id),
        additional_claims={"type": "email_verification"},
        expires_delta=datetime.timedelta(hours=24)
    )

    api_url = os.getenv('API_BASE_URL', 'http://localhost:5000')
    link_completo = f"{api_url}/api/auth/confirm-email?token={verification_token}"

    # Chama passando o LINK, não só o token
    send_verification_email(email, nome, link_completo)

    return {
        "sucesso": True,
        "id": new_user.id,
        "mensagem": "Usuário cadastrado com sucesso, verifique seu email para confirmação!"
    }


def create_admin_by_super(actor_id, data):
    """
    Cria um Admin de Restaurante (Nível 1).
    """
    super_email = os.getenv("SUPER_ADMIN_EMAIL")

    if User.query.filter_by(email=data['email']).first():
        raise ValueError("Email já cadastrado.")

    if actor_id != super_email:
        raise ValueError("Erro nas credenciais")



    # [NOVO] Validação de Força de Senha
    password = data['password']
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise ValueError(error_msg)


    hashed_password = generate_password_hash(password)

    new_admin = User(
        name=data['name'],
        email=data['email'],
        password_hash=hashed_password,
        role='admin',
        whatsapp=data.get('whatsapp')
    )

    db.session.add(new_admin)
    db.session.commit()
    return new_admin


def login_user(data):
    email = data.get('email')
    senha = data.get('password')
    usuario = User.query.filter_by(email=email).first()

    if not usuario or not check_password_hash(usuario.password_hash, senha):
        return {"sucesso": False, "message": "Email ou senha incorretos"}
    return {
        "sucesso": True,
        "user": {
            "id": usuario.id,
            "name": usuario.name,
            "email": usuario.email,
            "role": usuario.role,
            "whatsapp": usuario.whatsapp or ""
        },
        "message": "Login realizado com sucesso"
    }


def update_user_info(user_id, data):
    user = User.query.get(user_id)
    if not user:
        raise ValueError("Usuário não encontrado.")

    if 'name' in data: user.name = data['name'].strip()
    if 'whatsapp' in data: user.whatsapp = data['whatsapp']

    # [NOVO] Lógica de Senha com Validação
    if 'password' in data and data['password']:
        password = data['password']

        # Valida antes de trocar
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise ValueError(error_msg)

        user.password_hash = generate_password_hash(password)

    db.session.commit()

    # Busca o endereço ativo para retornar junto
    active_address = None
    for addr in user.addresses:
        if addr.is_active:
            active_address = {
                "street": addr.street,
                "number": addr.number,
                "neighborhood": addr.neighborhood,
                "complement": addr.complement
            }
            break

    return {
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role,
        'whatsapp': user.whatsapp,
        'address': active_address or {}
    }


def request_password_reset(email):
    """
    1. Verifica se e-mail existe.
    2. Gera token temporário.
    3. Envia e-mail.
    """
    user = User.query.filter_by(email=email).first()
    if not user:
        # Por segurança, não dizemos se o e-mail existe ou não
        return False

    # Gera um token JWT específico para reset, expirando em 30min
    reset_token = create_access_token(
        identity=str(user.id),
        expires_delta=datetime.timedelta(minutes=30),
        additional_claims={"type": "password_reset"}
    )

    # Chama o serviço de e-mail
    # --- NOVO: MONTA O LINK AQUI ---
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8000')
    link_reset = f"{frontend_url}/reset.html?token={reset_token}"

    # Chama passando o LINK
    send_reset_email(user.email, link_reset)
    return True


def reset_password_with_token(user_id, new_password):
    """
    Efetiva a troca. O user_id já vem extraído e validado do token na rota.
    """
    user = User.query.get(user_id)
    if not user:
        raise ValueError("Usuário inválido.")

    # Reutiliza sua validação de força de senha
    is_valid, error = validate_password_strength(new_password)
    if not is_valid:
        raise ValueError(error)

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    return True


def login_with_google(token):
    """
    Valida o token do Google e retorna o objeto User.
    """
    import requests  # Import aqui ou no topo

    # 1. Valida o token direto na API do Google
    google_verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={token}"
    response = requests.get(google_verify_url)

    if response.status_code != 200:
        raise ValueError("Token do Google inválido ou expirado.")

    google_data = response.json()
    meu_client_id = os.getenv('GOOGLE_CLIENT_ID')


    # 2. Segurança: Verifica se o token foi gerado para o SEU site
    if meu_client_id and google_data['aud'] != meu_client_id:
        raise ValueError("Token não pertence a este aplicativo.")

    email = google_data.get('email')
    name = google_data.get('name')

    if not email:
        raise ValueError("Google não forneceu o email.")

    # 3. Verifica se usuário já existe no banco
    user = User.query.filter_by(email=email).first()

    if not user:
        # Se não existe, CRIA automaticamente

        senha_aleatoria = secrets.token_urlsafe(16)
        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(senha_aleatoria),  # Usuário Google não tem senha
            role='client',
            is_verified=True  # Email do Google já é verificado
        )
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)

    return user


def confirmar_email(token):
    try:
        # Decodifica o token
        decoded = decode_token(token)

        # Se o token não for de email_verification nem magic_link_login, rejeita
        # (Adaptei aqui para aceitar os dois tipos, já que você tem os dois fluxos)
        tipo = decoded.get("type")
        if tipo not in ["email_verification", "magic_link_login"]:
            return {"sucesso": False, "erro": "Tipo de token inválido"}

        user_id = decoded["sub"]
        user = User.query.get(user_id)

        if not user:
            return {"sucesso": False, "erro": "Usuário não encontrado"}

        name = user.name
        role = user.role

        # Garante que está verificado
        if not user.is_verified:
            user.is_verified = True
            db.session.commit()

        # Gera token de login real para o usuário já entrar logado
        # (Nota: login_token é o token de sessão que vai pro cookie)
        login_token = create_token(user.id)

        resposta = {
            "name": name,
            "role": role,
            "id": user_id,
            "token": login_token,
            "whatsapp": user.whatsapp or "",
            "sucesso": True
        }
        return resposta
    except Exception as e:
        # Captura token expirado ou inválido sem travar o servidor
        return {"sucesso": False, "erro": str(e)}


def magic_link(data):
    """
    Solicitação de Magic Link (Login sem senha).
    Refatorado para retornar Dicionário em vez de JSON Response.
    """
    email = data.get('email')
    name = data.get('name')

    if not email:
        # return jsonify({'error': 'Email é obrigatório'}), 400  <-- COMENTADO (Errado no Service)
        return {"sucesso": False, "erro": "Email é obrigatório"}  # <-- NOVO (Certo no Service)

    user = User.query.filter_by(email=email).first()

    # --- CENÁRIO A: Usuário Novo (Auto-Cadastro Mágico) ---
    if not user:
        if not name:
            name = email.split('@')[0].replace('.', ' ').title()

        # Cria o usuário automaticamente
        user = User(name=name, email=email, is_verified=True, role='client')
        db.session.add(user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {"sucesso": False, "erro": "Erro ao criar usuário."}

    # --- CENÁRIO B: Usuário Existente ---

    # Gera token de curta duração (15 min) para o link
    magic_token = create_access_token(
        identity=str(user.id),
        additional_claims={"type": "magic_link_login"},
        expires_delta=datetime.timedelta(minutes=15)
    )

    

    if send_magic_link_email(user.email, user.name, magic_token): # <--- Passando só o token
        print(f"📧 Magic Link enviado para {user.email}")
        return {"sucesso": True, "mensagem": "Link enviado para seu e-mail."}
    else:
        return {"sucesso": False, "erro": "Erro ao enviar e-mail."}