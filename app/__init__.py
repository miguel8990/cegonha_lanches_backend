from flask import Flask
from flask_cors import CORS
from .errors import configure_errors
from config import Config
from .extensions import db, jwt, migrate, ma, socketio, limiter, redis_client
import os


def create_app():
    app = Flask(__name__)

    # 1. Carrega configurações básicas do Config.py
    app.config.from_object(Config)

    # ==========================================================================
    # CORREÇÃO CRÍTICA: Configuração do JWT ANTES de iniciar a extensão
    # ==========================================================================
    # Verifica a variável de ambiente (garante que lê 'production' corretamente)
    env_flask = os.getenv('FLASK_ENV', 'development')
    is_production = env_flask == 'production'

    print(f"🔧 Iniciando App. Ambiente: {env_flask} | Modo Produção: {is_production}")

    app.config["JWT_TOKEN_LOCATION"] = ["cookies", "headers"]
    app.config["JWT_ACCESS_COOKIE_NAME"] = "token"

    # Força configurações de cookie seguro se for produção
    if is_production:
        app.config["JWT_COOKIE_SECURE"] = True
        app.config["JWT_COOKIE_SAMESITE"] = "None"
        app.config["JWT_COOKIE_CSRF_PROTECT"] = False
    else:
        app.config["JWT_COOKIE_SECURE"] = False
        app.config["JWT_COOKIE_SAMESITE"] = "Lax"
        app.config["JWT_COOKIE_CSRF_PROTECT"] = False

    # ==========================================================================

    # 2. Configura REDIS
    redis_url = os.getenv('REDIS_URI')
    if redis_url:
        app.config['RATELIMIT_STORAGE_URI'] = redis_url
        app.config['REDIS_URL'] = redis_url
        if redis_client:
            redis_client.init_app(app)

    # 3. Inicia Extensões (AGORA COM AS CONFIGURAÇÕES CERTAS CARREGADAS)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)  # <--- Agora ele vai ler o JWT_COOKIE_SECURE = True
    ma.init_app(app)
    limiter.init_app(app)

    # 4. Configura CORS
    # Adicionando o Frontend explicitamente para garantir
    frontend_url = os.getenv('FRONTEND_URL', 'https://miguel8990.github.io')

    # Extrai o domínio base caso a URL venha com subpastas (para o CORS aceitar)
    # Ex: https://miguel8990.github.io/projeto -> https://miguel8990.github.io
    origins_list = [
        "https://miguel8990.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    CORS(app, resources={r"/*": {"origins": origins_list}}, supports_credentials=True)

    # 5. Registro de Blueprints
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

    # 6. Inicia SocketIO
    socketio.init_app(app, cors_allowed_origins="*", message_queue=redis_url)

    return app