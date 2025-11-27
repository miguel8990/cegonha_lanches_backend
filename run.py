from app import create_app

app = create_app()

# Cria as tabelas no banco automaticamente se não existirem
#with app.app_context():
#    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)