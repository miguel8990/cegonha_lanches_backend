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





# Instancia plugins globalmente (ainda sem o app)



def create_app():
    app = Flask(__name__)
    # ... configurações iniciais ...
    app.config.from_object(Config)
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app)
    redis_client.init_app(app)
    # Importação das Rotas (Blueprints)
    # ANTES: from .routes_menu import bp_menu
    import os
    from . import models
    # LISTA DE ORIGENS PERMITIDAS
    # Adicione aqui:
    # 1. O seu localhost (para testes)
    # 2. O seu link final do GitHub Pages (quando você criar)
    origins_list = [
        "https://miguel8990.github.io/cegonha_lanches_frontend/",  # <--- Substitua pelo link real do GitHub
        "https://www.cegonhalanches.com.br"  # (Opcional) Se usar domínio próprio no futuro
    ]
    if os.getenv('FLASK_DEBUG') == '1':
        print("🔓 Modo Desenvolvimento: Liberando localhost no CORS")
        origins_list.extend([
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:5500",  # VS Code Live Server (comum)
            "http://127.0.0.1:5500"
        ])

    CORS(app, resources={r"/api/*": {"origins": origins_list}})
    # AGORA: Importamos da pasta routes e do arquivo menu
    from .routes.routes_menu import bp_menu
    from .routes.routes_orders import bp_orders
    from .routes.routes_auth import bp_auth
    from .routes.routes_payment import bp_payment
    from .routes.routes_delivery import bp_delivery
    from .routes.routes_reports import bp_reports

    # Registro das Rotas (Isso continua igual, ou você pode ajustar o prefixo se quiser)
    app.register_blueprint(bp_menu, url_prefix='/api/menu')
    app.register_blueprint(bp_orders, url_prefix='/api/orders')
    app.register_blueprint(bp_auth, url_prefix='/api/auth')
    app.register_blueprint(bp_payment, url_prefix='/api/payment')
    app.register_blueprint(bp_address, url_prefix='/api/address')
    app.register_blueprint(bp_chat, url_prefix='/api/chat')
    app.register_blueprint(bp_config, url_prefix='/api/config')
    app.register_blueprint(bp_delivery, url_prefix='/api/delivery')
    app.register_blueprint(bp_reports, url_prefix='/api/reports')
    configure_errors(app)
    import os
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.register_blueprint(bp_upload, url_prefix='/api/upload')

    return app