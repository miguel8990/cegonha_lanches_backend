from ..models import User, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token


def register_user(name, email, password):
    # 1. Verifica se o usuário já existe
    if User.query.filter_by(email=email).first():
        # Retorna None ou levanta um erro para a rota saber que falhou
        raise ValueError("Este email já está cadastrado.")

    # 2. Criptografa a senha
    hashed_password = generate_password_hash(password)

    # 3. Cria e salva o usuário
    new_user = User(
        name=name,
        email=email,
        password_hash=hashed_password,
        is_admin=False
    )

    db.session.add(new_user)
    db.session.commit()

    return new_user


def login_user(email, password):
    # 1. Busca o usuário
    user = User.query.filter_by(email=email).first()

    # 2. Verifica se existe e se a senha bate
    if user and check_password_hash(user.password_hash, password):
        # 3. Gera o Token (o "crachá" de acesso)
        access_token = create_access_token(identity=str(user.id))
        return {
            'token': access_token,
            'user': {'id': user.id, 'name': user.name, 'email': user.email}
        }

    # Se falhar, retornamos None
    return None