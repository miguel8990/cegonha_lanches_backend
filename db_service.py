from app import create_app
from app.extensions import db
from app.models import User, Product, Order, Coupon, Neighborhood
from werkzeug.security import generate_password_hash
import sys


# Inicializa a aplicação para ter acesso ao banco
app = create_app()
#digite python -i db_service.py no terminal

def help():
    """Mostra os comandos disponíveis."""
    print("\n--- Comandos Disponíveis ---")
    print("list_users()              -> Lista todos os usuários")
    print("list_admins()             -> Lista apenas admins e super_admins")
    print("set_admin(email)          -> Promove usuário a 'admin'")

    print("reset_password(email, new_pass) -> Troca senha de um usuário")
    print("list_products()           -> Lista produtos")
    print("toggle_product(id)        -> Ativa/Desativa um produto")
    print("list_orders()             -> Lista os últimos 10 pedidos")
    print("----------------------------\n")


# --- USUÁRIOS ---

def list_users():
    with app.app_context():
        users = User.query.all()
        print(f"\n{'ID':<5} {'NOME':<30} {'EMAIL':<30} {'ROLE':<15} {'VERIFICADO'}")
        print("-" * 100)
        for u in users:
            print(f"{u.id:<5} {u.name[:29]:<30} {u.email[:29]:<30} {u.role:<15} {u.is_verified}")
        print("-" * 100)


def list_admins():
    with app.app_context():
        admins = User.query.filter(User.role.in_(['admin', 'super_admin'])).all()
        print("\n--- LISTA DE ADMINISTRADORES ---")
        for u in admins:
            print(f"ID: {u.id} | Nome: {u.name} | Email: {u.email} | Nível: {u.role}")


def delete_user(email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ Usuário {email} não encontrado.")
            return

        db.session.delete(user)
        db.session.commit()
        print(f"User:{user} deletado!!")


def set_admin(email):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ Usuário {email} não encontrado.")
            return

        user.role = 'admin'
        db.session.commit()
        print(f"✅ Sucesso! {user.name} agora é um ADMIN (Gerente).")


def reset_password(email, new_password):
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ Usuário {email} não encontrado.")
            return

        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        print(f"✅ Senha de {user.email} alterada com sucesso!")


# --- PRODUTOS ---

def list_products():
    with app.app_context():
        products = Product.query.order_by(Product.id).all()
        print(f"\n{'ID':<5} {'NOME':<30} {'PREÇO':<10} {'ESTOQUE':<10} {'ATIVO'}")
        print("-" * 80)
        for p in products:
            status = "✅" if p.is_available else "❌"
            estoque = p.stock_quantity if p.stock_quantity is not None else "∞"
            print(f"{p.id:<5} {p.name[:29]:<30} R$ {p.price:<7} {estoque:<10} {status}")


def toggle_product(product_id):
    with app.app_context():
        p = Product.query.get(product_id)
        if not p:
            print("Produto não encontrado.")
            return

        p.is_available = not p.is_available
        db.session.commit()
        status = "Disponível" if p.is_available else "Indisponível"
        print(f"✅ Produto '{p.name}' agora está {status}.")


# --- PEDIDOS ---

def list_orders():
    with app.app_context():
        # Pega os últimos 10 pedidos
        orders = Order.query.order_by(Order.id.desc()).limit(10).all()
        print(f"\n{'ID':<5} {'DATA':<20} {'CLIENTE':<20} {'STATUS':<15} {'TOTAL'}")
        print("-" * 80)
        for o in orders:
            print(
                f"{o.id:<5} {o.date_created.strftime('%d/%m %H:%M'):<20} {o.customer_name[:19]:<20} {o.status:<15} R$ {o.total_price}")


# Executa automaticamente o help se rodar o script
if __name__ == "__main__":
    if __name__ == "__main__":
        # Dicionário que conecta o "texto digitado" à "função real"
        available_commands = {
            "help": help,
            "list_users": list_users,
            "list_admins": list_admins,
            "list_products": list_products,
            "list_orders": list_orders,
            # Comandos com argumentos:
            "set_admin": set_admin,  # Espera 1 argumento (email)
            "delete_user": delete_user,  # Espera 1 argumento (email)
            "toggle_prod": toggle_product,  # Espera 1 argumento (id)
            # "reset_pass": reset_password,  # Espera 2 argumentos (email, senha)
        }

        # Se não tiver argumentos, mostra ajuda
        if len(sys.argv) < 2:
            help()
            print("\n❌ Erro: Nenhum comando informado.")
            print("👉 Exemplo de uso: python db_service.py list_orders")
            sys.exit(1)

        command_name = sys.argv[1]
        args = sys.argv[2:]

        # Verifica se o comando existe
        if command_name not in available_commands:
            print(f"❌ Comando '{command_name}' não existe.")
            help()
            sys.exit(1)

        # Executa a função passando os argumentos (se houver)
        try:
            print(f"🔄 Executando: {command_name}...")
            func = available_commands[command_name]
            func(*args)  # O asterisco desenrola a lista de argumentos
            print("\n🏁 Concluído.")
        except TypeError as e:
            print(f"❌ Erro nos argumentos: O comando '{command_name}' esperava outros dados.")
            print(f"Detalhe técnico: {e}")
        except Exception as e:
            print(f"❌ Erro inesperado: {e}")
