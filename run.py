from app import create_app
import os
from app.extensions import socketio

app = create_app()

# Cria as tabelas no banco automaticamente se não existirem
#with app.app_context():
#    db.create_all()

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    #app.run(debug=True)
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)