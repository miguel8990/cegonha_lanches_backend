from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Instanciamos tudo aqui, mas sem ligar ao 'app' ainda
db = SQLAlchemy()
ma = Marshmallow()
jwt = JWTManager()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)