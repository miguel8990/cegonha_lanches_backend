from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models import User

def admin_required():
    """
    Nível 1: Permite 'admin' (Restaurante) e 'super_admin' (Você).
    Usado em: Menu, Pedidos, Pagamentos.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)

            # Verifica se existe e se tem permissão mínima
            if not current_user or current_user.role not in ['admin', 'super_admin']:
                return jsonify(msg='Acesso negado. Área restrita a administradores.'), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper

def super_admin_required():
    """
    Nível 2 (DEUS): Permite APENAS 'super_admin'.
    Usado em: Criar novos admins, deletar usuários, configurações sensíveis.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            current_user = User.query.get(user_id)

            # Verifica se é estritamente super_admin
            if not current_user or current_user.role != 'super_admin':
                return jsonify(msg='Acesso negado. Requer nível Super Admin.'), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper