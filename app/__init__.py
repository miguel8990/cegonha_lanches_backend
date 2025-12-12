from flask import Flask
from flask_cors import CORS
from .errors import configure_errors
from config import Config
from .extensions import db, jwt, migrate, ma, socketio
from .routes.routes_address import bp_address
from .routes.routes_chat import bp_chat
from .routes.routes_upload import bp_upload
from .extensions import db, jwt, migrate, ma, limiter, redis_client
from .routes.routes_config import bp_config


def create_app():
    app = Flask(__name__)

    # 1. Carrega configurações do Config.py
    app.config.from_object(Config)

    # 2. PEGA O REDIS ANTES DE INICIAR OS PLUGINS
    import os
    redis_url = os.getenv('REDIS_URI')  # Ex: redis://localhost:6379/0

    # 3. CONFIGURA O FLASK PARA USAR O REDIS (Se ele existir)
    if redis_url:
        # Configuração para o Flask-Limiter parar de reclamar da memória
        app.config['RATELIMIT_STORAGE_URI'] = redis_url

        # Configuração para o redis_client (Flask-Redis) genérico
        app.config['REDIS_URL'] = redis_url

        if redis_client:
            redis_client.init_app(app)

        # ... Inicia Banco e Migrations ...
    db.init_app(app)
    migrate.init_app(app, db)

    # ... Inicia JWT e Marshmallow ...
    jwt.init_app(app)
    ma.init_app(app)

    # 4. INICIA O LIMITER (Agora ele vai ler a config do Redis acima)
    limiter.init_app(app)

    # 5. INICIA O REDIS CLIENT GERAL (Faltava isso!)
    # Isso permite que você use redis_client.set() nas suas rotas


    # ... Configurações de Cookie JWT (Mantive seu código igual) ...
    is_production = os.getenv('FLASK_ENV') == 'production'
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_ACCESS_COOKIE_NAME"] = "token"
    app.config["JWT_COOKIE_SECURE"] = is_production
    app.config["JWT_COOKIE_SAMESITE"] = "None" if is_production else "Lax"
    if is_production:
        app.config["JWT_COOKIE_SECURE"] = True
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False

    # ... CORS (Mantive igual) ...
    from . import models
    CORS(app, resources={r"/*": {"origins": [
        "https://miguel8990.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]}}, supports_credentials=True)

    # ... Importação e Registro de Blueprints (Mantive igual) ...
    from .routes.routes_menu import bp_menu
    from .routes.routes_orders import bp_orders
    from .routes.routes_auth import bp_auth
    from .routes.routes_payment import bp_payment
    from .routes.routes_delivery import bp_delivery
    from .routes.routes_reports import bp_reports
    from .routes.routes_address import bp_address
    from .routes.routes_chat import bp_chat
    from .routes.routes_config import bp_config
    from .routes.routes_upload import bp_upload

    app.register_blueprint(bp_menu, url_prefix='/api/menu')
    app.register_blueprint(bp_orders, url_prefix='/api/orders')
    app.register_blueprint(bp_auth, url_prefix='/api/auth')
    app.register_blueprint(bp_payment, url_prefix='/api/payment')
    app.register_blueprint(bp_address, url_prefix='/api/address')
    app.register_blueprint(bp_chat, url_prefix='/api/chat')
    app.register_blueprint(bp_config, url_prefix='/api/config')
    app.register_blueprint(bp_delivery, url_prefix='/api/delivery')
    app.register_blueprint(bp_reports, url_prefix='/api/reports')

    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.register_blueprint(bp_upload, url_prefix='/api/upload')

    configure_errors(app)

    # 6. INICIA O SOCKETIO
    # O message_queue é útil se você tiver vários workers (Gunicorn),
    # se for só um servidor simples, nem precisaria, mas não faz mal ter.
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        message_queue=redis_url
    )

    return app