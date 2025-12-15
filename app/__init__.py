from flask import Flask
from flask_cors import CORS
from .errors import configure_errors
from config import Config
from .extensions import db, jwt, migrate, ma, socketio, limiter, redis_client
from werkzeug.middleware.proxy_fix import ProxyFix
import os


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ==========================================================================
    # CORREÇÃO: Detecção robusta de Produção
    # ==========================================================================
    # Se FLASK_ENV for production OU se estiver rodando no Render ('RENDER' existe)
    is_production = os.getenv('FLASK_ENV') == 'production' or os.getenv('RENDER') is not None

    if is_production:
        # ProxyFix é essencial no Render para HTTPS funcionar
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    print(f"🔧 Ambiente: {'Produção' if is_production else 'Dev'} | Secure Cookies: {is_production}")

    # JWT Cookie Configuration
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_ACCESS_COOKIE_NAME"] = "token"  # Garante o nome certo
    app.config["JWT_ACCESS_COOKIE_PATH"] = "/"

    # 🔥 CORREÇÃO DE COOKIES CROSS-ORIGIN
    if is_production:
        print("🌍 Modo Produção: SameSite=None, Secure=True (Cross-Origin Ativo)")
        app.config["JWT_COOKIE_SECURE"] = True
        app.config["JWT_COOKIE_SAMESITE"] = "None"  # Obrigatório para GitHub -> Render
    else:
        print("💻 Modo Dev: SameSite=Lax, Secure=False")
        app.config["JWT_COOKIE_SECURE"] = False
        app.config["JWT_COOKIE_SAMESITE"] = "Lax"

    app.config["JWT_COOKIE_CSRF_PROTECT"] = False





    # ==========================================================================
    # REDIS
    # ==========================================================================
    redis_url = os.getenv('REDIS_URI')
    if redis_url:
        app.config['RATELIMIT_STORAGE_URI'] = redis_url
        app.config['REDIS_URL'] = redis_url
        if redis_client:
            redis_client.init_app(app)

    # ==========================================================================
    # EXTENSÕES
    # ==========================================================================
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    limiter.init_app(app)

    # ==========================================================================
    # 🔥 CORREÇÃO CRÍTICA DO CORS
    # ==========================================================================
    frontend_urls = [
        "https://miguel8990.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5000"  # Para testes locais
    ]

    CORS(
        app,
        supports_credentials=True,  # 🔥 ESSENCIAL para cookies
        resources={
            r"/api/*": {
                "origins": frontend_urls,
                "allow_headers": ["Content-Type", "Authorization"],
                "expose_headers": ["Set-Cookie"],
                "methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
            }
        }
    )

    # ==========================================================================
    # BLUEPRINTS
    # ==========================================================================
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
    socketio.init_app(app, cors_allowed_origins="*", message_queue=redis_url)

    return app