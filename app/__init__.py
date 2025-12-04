from flask import Flask
from flask_cors import CORS
from .errors import configure_errors
from config import Config
from .extensions import db, jwt, migrate, ma
from .routes.routes_address import bp_address
from .routes.routes_chat import bp_chat
from .routes.routes_upload import bp_upload
from .extensions import db, jwt, migrate, ma, limiter
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
    # Importação das Rotas (Blueprints)
    # ANTES: from .routes_menu import bp_menu

    from . import models

    CORS(app)
    # AGORA: Importamos da pasta routes e do arquivo menu
    from .routes.routes_menu import bp_menu
    from .routes.routes_orders import bp_orders
    from .routes.routes_auth import bp_auth
    from .routes.routes_payment import bp_payment

    # Registro das Rotas (Isso continua igual, ou você pode ajustar o prefixo se quiser)
    app.register_blueprint(bp_menu, url_prefix='/api/menu')
    app.register_blueprint(bp_orders, url_prefix='/api/orders')
    app.register_blueprint(bp_auth, url_prefix='/api/auth')
    app.register_blueprint(bp_payment, url_prefix='/api/payment')
    app.register_blueprint(bp_address, url_prefix='/api/address')
    app.register_blueprint(bp_chat, url_prefix='/api/chat')
    app.register_blueprint(bp_config, url_prefix='/api/config')
    configure_errors(app)
    import os
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.register_blueprint(bp_upload, url_prefix='/api/upload')

    return app