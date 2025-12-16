from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from flask_redis import FlaskRedis
from flask import request
# Instanciamos tudo aqui, mas sem ligar ao 'app' ainda

def get_real_ip():
    # Tenta pegar o cabeçalho do Cloudflare, se não existir, usa o padrão
    if request:
        return request.headers.get("CF-Connecting-IP") or get_remote_address()
    return "127.0.0.1"





db = SQLAlchemy()
ma = Marshmallow()
jwt = JWTManager()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)
redis_client = FlaskRedis()

socketio = SocketIO(cors_allowed_origins="*")