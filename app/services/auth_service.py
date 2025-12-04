import re
from ..models import User, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from datetime import timedelta
from .email_services import send_reset_email

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


def register_user(name, email, password, whatsapp=None, street=None, number=None, neighborhood=None, complement=None):
    """
    Registro Público (App do Cliente).
    Sempre cria com role='client'.
    """
    # 1. Validação de Email Duplicado
    if User.query.filter_by(email=email).first():
        raise ValueError("Este email já está cadastrado.")

    # 2. [NOVO] Validação de Força de Senha
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise ValueError(error_msg)

    hashed_password = generate_password_hash(password)

    new_user = User(
        name=name,
        email=email,
        password_hash=hashed_password,
        role='client',  # Força nível baixo
        whatsapp=whatsapp
    )

    db.session.add(new_user)
    db.session.commit()

    return new_user


def create_admin_by_super(actor_id, data):
    """
    Cria um Admin de Restaurante (Nível 1).
    """
    if User.query.filter_by(email=data['email']).first():
        raise ValueError("Email já cadastrado.")

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


def login_user(email, password):
    user = User.query.filter_by(email=email).first()

    if user and check_password_hash(user.password_hash, password):
        access_token = create_access_token(identity=str(user.id))
        return {
            'token': access_token,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role
            }
        }
    return None


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


# app/services/auth_service.py
from datetime import timedelta
# ... importações existentes ...
from .email_services import send_reset_email  # Importe o novo serviço


def request_password_reset(email):
    """
    1. Verifica se e-mail existe.
    2. Gera token temporário.
    3. Envia e-mail.
    """
    user = User.query.filter_by(email=email).first()
    if not user:
        # Por segurança, não dizemos se o e-mail existe ou não,
        # apenas retornamos sucesso falso ou True genérico.
        # Mas para simplificar aqui, vamos retornar False.
        return False

    # Gera um token JWT específico para reset, expirando em 30min
    reset_token = create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(minutes=30),
        additional_claims={"type": "password_reset"}  # Marca d'água para saber que é reset
    )

    # Chama o serviço de e-mail
    send_reset_email(user.email, reset_token)
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