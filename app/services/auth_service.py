from ..models import User, db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token


def register_user(name, email, password, whatsapp=None, street=None, number=None, neighborhood=None, complement=None):
    """
    Registro Público (App do Cliente).
    Sempre cria com role='client'.
    """
    if User.query.filter_by(email=email).first():
        raise ValueError("Este email já está cadastrado.")

    hashed_password = generate_password_hash(password)

    new_user = User(
        name=name,
        email=email,
        password_hash=hashed_password,
        role='client',  # Força nível baixo
        whatsapp=whatsapp,
        street=street,
        number=number,
        neighborhood=neighborhood,
        complement=complement
    )

    db.session.add(new_user)
    db.session.commit()
    return new_user


def create_admin_by_super(actor_id, data):
    """
    Cria um Admin de Restaurante (Nível 1).
    Só pode ser executado se o actor_id for Super Admin (Verificado no decorator, mas reforçado aqui).
    """
    # Verifica duplicidade
    if User.query.filter_by(email=data['email']).first():
        raise ValueError("Email já cadastrado.")

    hashed_password = generate_password_hash(data['password'])

    new_admin = User(
        name=data['name'],
        email=data['email'],
        password_hash=hashed_password,
        role='admin',  # Cria com poderes de restaurante
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
                'role': user.role  # Retorna a role pro Frontend esconder botões
            }
        }
    return None