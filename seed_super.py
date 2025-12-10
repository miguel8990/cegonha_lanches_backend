from app import create_app
from app.extensions import db
from app.models import Product, User
from werkzeug.security import generate_password_hash
import json
import os
from app.models import StoreSchedule

app = create_app()


def create_super_admin():
    """
    Cria o Super Admin se não existir.
    """
    print("📦 Resetando tabela de super_user...")





    SUPER_EMAIL = os.getenv("SUPER_ADMIN_EMAIL")
    SUPER_PASS = os.getenv("SUPER_ADMIN_PASSWORD")

    if not SUPER_EMAIL or not SUPER_PASS:
        print("❌ ERRO: Variáveis 'SUPER_ADMIN_EMAIL' ou 'SUPER_ADMIN_PASSWORD' ausentes")
        return

    try:
        # --- PASSO 1: LIMPEZA TOTAL ---
        # Busca TODOS os super admins (não apenas o primeiro)
        existing_supers = User.query.filter_by(role="super_admin").all()

        if existing_supers:
            count = 0
            for u in existing_supers:
                # Opcional: Se quiser preservar o SEU super atual (pelo email), adicione um if aqui.
                # Mas para garantir unicidade total, melhor apagar tudo e recriar.
                print(f"   🗑️  Removendo antigo super: {u.email} (ID: {u.id})")
                db.session.delete(u)
                count += 1

            db.session.commit()
            print(f"✅ Limpeza concluída. {count} super admin(s) removido(s).")
        else:
            print("ℹ️  Nenhum super admin encontrado para remover.")

        print(f"👤 Criando Super Admin: ...")

        super_admin = User(
            name="Super Admin Deus",
            email=SUPER_EMAIL,
            password_hash=generate_password_hash(SUPER_PASS),
            role="super_admin",
            whatsapp="0000000000",
            is_verified=True
        )

        db.session.add(super_admin)
        db.session.commit()
        print("✅ Super Admin criado!")

    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro crítico ao redefinir super admin: {str(e)}")

if __name__ == '__main__':
    with app.app_context():
        # Cria tabelas se não existirem
        db.create_all()

        # Popula dados
        create_super_admin()
