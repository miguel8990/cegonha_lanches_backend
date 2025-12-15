from app import create_app
from app.extensions import db
from app.models import Product, User, ChatMessage, Address
from werkzeug.security import generate_password_hash
import json
import os
from app.models import StoreSchedule # Adicione o import

app = create_app()


def apagar_tudo():
    """
    ⚠️ PERIGO: Função para zerar o banco de dados completamente.
    Apaga todas as tabelas e as cria novamente.
    """
    print("🧨 ATENÇÃO: INICIANDO LIMPEZA TOTAL DO BANCO DE DADOS (DROP ALL)...")
    try:
        # Apaga todas as tabelas existentes (Orders, Users, Products, etc.)
        db.drop_all()
        # Recria as tabelas vazias baseadas nos Models
        db.create_all()
        db.session.commit()
        print("✅ Banco de dados zerado e tabelas recriadas com sucesso!")
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao tentar limpar o banco: {str(e)}")

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

                msgs_deleted = ChatMessage.query.filter_by(user_id=u.id).delete()
                if msgs_deleted > 0:
                    print(f"      ↳ 💬 {msgs_deleted} mensagens de chat removidas.")
                Address.query.filter_by(user_id=u.id).delete()
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



def get_common_options():
    """
    Retorna as listas padrão usadas em quase todos os lanches.
    Baseado no api.js.
    """
    acompanhamentos = [
        {"nome": "Porção de batata porção inteira", "price": 30.0},
        {"nome": "Porção de batata porção 1/2", "price": 20.0},
        {"nome": "Bacon e cheddar porção inteira", "price": 40.0},
        {"nome": "Bacon e cheddar porção 1/2", "price": 30.0},
        {"nome": "Calabresa porção inteira", "price": 40.0},
        {"nome": "Calabresa porção 1/2", "price": 25.0},
    ]

    adicionais = [
        {"nome": "Hambúrguer", "price": 2.5},
        {"nome": "Hambúrguer Artesanal", "price": 5.0},
        {"nome": "Mussarela", "price": 3.0},
        {"nome": "Bacon", "price": 3.0},
        {"nome": "Salsicha", "price": 2.0},
        {"nome": "Ovo", "price": 2.0},
        {"nome": "Requeijão ou cheddar", "price": 2.0},
        {"nome": "Batata Palha", "price": 3.0},
    ]

    bebidas = [
        {"nome": "Cotuba 2L", "price": 10.0},
        {"nome": "Cotuba 600ml", "price": 6.0},
        {"nome": "Cotuba Lata 350ml", "price": 5.0},
        {"nome": "Coca-Cola 2L", "price": 12.0},
        {"nome": "Coca-Cola 600ml", "price": 6.0},
        {"nome": "Coca-Cola Lata 350ml", "price": 5.0},
        {"nome": "Skol Lata 350ml", "price": 5.0},
        {"nome": "Antartica Lata 350ml", "price": 5.0},
    ]

    return acompanhamentos, adicionais, bebidas


def seed_products():
    """
    Popula o banco com todos os produtos do api.js.
    """
    print("📦 Resetando tabela de produtos...")
    try:
        db.session.query(Product).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Erro ao limpar produtos: {e}")

    # Carrega as listas comuns
    acompanhamentos, adicionais, bebidas = get_common_options()

    # Lista completa baseada no api.js
    all_products = [
        {
            "name": "FALCÃO",
            "price": 30.0,
            "category": "Lanche",
            "description": "Pão, presunto, mussarela, ovo, requeijão, bacon, milho, alface, tomate. (Opções de Carnes: Frango, Lombo ou Filé)",
            "image_url": "assets/falcao.jpg",
            "carnes": [{"nome": "Frango", "price": 0}, {"nome": "Lombo", "price": 0}, {"nome": "Filé", "price": 0}]
        },
        {
            "name": "ÁGUIA",
            "price": 35.0,
            "category": "Lanche",
            "description": "Pão, Hambúrguer da casa, duas fatias de presunto, Mussarela, ovo, Bacon, Cenoura, Milho, Alface, Tomate.",
            "image_url": "assets/aguia.jpg",
            "carnes": [{"nome": "Hambúrguer", "price": 0}]
        },
        {
            "name": "CALOPSITA",
            "price": 30.0,
            "category": "Lanche",
            "description": "Pão, hambúrguer, presunto, mussarela, ovo, salsicha, bacon, creme de leite, milho, alface, tomate.",
            "image_url": "assets/calopsita.jpg",
            "carnes": [{"nome": "Hambúrguer", "price": 0}]
        },
        {
            "name": "CANÁRIO",
            "price": 30.0,
            "category": "Lanche",
            "description": "Pão, hambúrguer, presunto, mussarela, 2 ovos, bacon, requeijão, milho, alface, tomate.",
            "image_url": "assets/canario.jpg",
            "carnes": [{"nome": "Hambúrguer", "price": 0}]
        },
        {
            "name": "CEGONHA-TURBO",
            "price": 45.0,
            "category": "Lanche",
            "description": "Pão, hambúrguer, presunto, mussarela, ovo, requeijão, bacon, lombo, frango, filé, salsicha, milho, tomate, alface.",
            "image_url": "assets/cegonha-turbo.jpg",
            "carnes": [{"nome": "Hambúrguer", "price": 0}]
        },
        {
            "name": "BEM-TE-VI",
            "price": 25.0,
            "category": "Lanche",
            "description": "Pão, hambúrguer, presunto, mussarela, ovo, bacon, milho, alface, tomate.",
            "image_url": "assets/bem-te-vi.jpg",
            "carnes": [{"nome": "Hambúrguer", "price": 0}]
        },
        {
            "name": "BEIJA-FLOR",
            "price": 26.0,
            "category": "Lanche",
            "description": "Pão, hambúrguer, presunto, mussarela, ovo, requeijão, cenoura, milho, ervilha, alface, tomate.",
            "image_url": "assets/beija-flor.jpg",
            "carnes": [{"nome": "Hambúrguer", "price": 0}]
        },
        {
            "name": "BEM-TE-VI-ARTESANAL",
            "price": 30.0,
            "category": "Lanche",
            "description": "Pão, Hambúrguer da casa, presunto, mussarela, ovo, bacon, cenoura, milho, alface, tomate.",
            "image_url": "assets/bem-te-vi-artesanal.jpg",
            "carnes": [{"nome": "Hambúrguer da casa", "price": 0}]
        },
        {
            "name": "VEGETARIANO",
            "price": 18.0,
            "category": "Lanche",
            "description": "Pão, 2 mussarelas, ovo, requeijão, cenoura, milho, alface, tomate, batata palha.",
            "image_url": "assets/vegetariano.jpg",
            "carnes": []  # Sem carne
        },
        {
            "name": "CEGONHA-KIDS",
            "price": 20.0,
            "category": "Lanche",
            "description": "Pão, hambúrguer, 2 fatias de presunto, mussarela, ovo, bacon, cheddar, milho, alface, tomate, batata palha.",
            "image_url": "assets/kids.jpg",
            "carnes": [{"nome": "Hambúrguer", "price": 0}]
        },
        {
            "name": "X-CAIPIRA",
            "price": 30.0,
            "category": "Lanche",
            "description": "Pão, hambúrguer de linguiça suína, presunto, mussarela, ovo, bacon, cenoura, milho, alface, tomate.",
            "image_url": "assets/x-caipira.jpg",
            "carnes": [{"nome": "Hambúrguer de linguiça suína", "price": 0}]
        },
        # --- COMBOS ---
        {
            "name": "COMBO CALOPSITA + BATATA FRITA",
            "price": 45.0,
            "category": "Combo",
            "description": "Pão, Hambúrguer, Presunto, Ovo, Salsicha, Bacon, Creme de Leite, Alface, Tomate, Milho + 250G de Batata Frita",
            "image_url": "assets/combo-calopsita.jpg",
            "carnes": []
        },
        {
            "name": "COMBO-ESPECIAL",
            "price": 80.0,
            "category": "Combo",
            "description": "3 BEM-TE-VI: Pão, hambúrguer, presunto, mussarela, ovo, bacon, milho, alface, tomate + 1 Cotuba 2L",
            "image_url": "assets/combo-especial.jpg",
            "carnes": []
        }
    ]

    print(f"🍔 Inserindo {len(all_products)} produtos...")

    for p in all_products:
        # Monta o JSON de detalhes unificando as listas comuns com as específicas do produto
        details_structure = {
            "carnes": p["carnes"],
            "acompanhamentos": acompanhamentos,
            "adicionais": adicionais,
            "bebidas": bebidas
        }

        new_prod = Product(
            name=p['name'],
            description=p['description'],
            price=p['price'],
            image_url=p['image_url'],
            category=p['category'],
            is_available=True,
            details_json=json.dumps(details_structure)
        )
        db.session.add(new_prod)

    print("🥤 Inserindo Bebidas...")

    # Lista explícita para ter controle total dos nomes e preços
    bebidas_fixas = [
        {"nome": "Cotuba 2L", "price": 10.0, "img": "cotuba-2l.jpg"},
    ]

    for b in bebidas_fixas:
        # Se a imagem não existir, usa uma genérica (você precisa ter essa imagem ou alterar aqui)
        imagem_final = f"assets/{b['img']}"

        nova_bebida = Product(
            name=b['nome'],
            description="Bebida gelada",
            price=b['price'],
            image_url=imagem_final,
            category="Bebida",
            is_available=True,
            details_json=json.dumps({})  # Bebidas simples não tem personalização por padrão
        )
        db.session.add(nova_bebida)

    db.session.commit()
    print("✅ Menu (Lanches + Bebidas) populado com sucesso!")


def seed_schedule():
    """Cria os horários padrão se não existirem"""
    if StoreSchedule.query.count() > 0:
        print("⏰ Horários já configurados.")
        return

    print("⏰ Criando horários padrão...")
    # 0=Domingo (Fechado), 1-6 (Aberto 18:30-22:30)
    padrao_dias = []
    for i in range(7):
        fechado = (i == 0)  # Domingo fechado por padrão
        dia = StoreSchedule(
            day_of_week=i,
            open_time="18:30",
            close_time="22:30",
            is_closed=fechado
        )
        db.session.add(dia)

    db.session.commit()
    print("✅ Horários criados!")


def seed_database():
    """
    Função responsável por criar as tabelas e popular o banco com dados iniciais.
    """

    # 'with app.app_context()' cria o ambiente necessário para o script acessar
    # as configurações do banco de dados do Flask.
    with app.app_context():
        create_super_admin()
        print("1. Verificando/Criando tabelas...")
        # CRUCIAL: Este comando cria as tabelas no banco se elas não existirem.
        # Sem isso, o erro 'relation product does not exist' continuará.
        db.create_all()



        # =======================================================
        # 🛡️ CONTROLE SEGURO VIA VARIÁVEL DE AMBIENTE
        # Só apaga se no Render estiver escrito exatamente "true"
        # =======================================================
        should_reset = os.getenv("DELETE_ALL_DB", "false").lower() == "true"

        if should_reset:
            print("🚨 VARIÁVEL 'DELETE_ALL_DB' DETECTADA COMO TRUE!")
            apagar_tudo()
        else:
            print("ℹ️ Modo de segurança: O banco NÃO será apagado (DELETE_ALL_DB não é 'true').")
        # =======================================================

        print("2. Verificando se já existem dados...")
        # === AQUI ESTÁ A VERIFICAÇÃO QUE VOCÊ PEDIU ===
        # Product.query.first() tenta pegar o primeiro item da tabela.
        # Se retornar algo (não for None), significa que o banco já tem dados.
        if Product.query.first():
            print(">>> O banco de dados JÁ possui produtos. Seed cancelado para evitar duplicatas.")
            return  # O 'return' encerra a função aqui, nada abaixo será executado.


        # Adiciona o objeto à sessão (prepara para salvar)
        seed_products()
        seed_schedule()

        print(">>> Sucesso! Dados inseridos.")


if __name__ == "__main__":
    seed_database()
