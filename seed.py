from app import create_app
from app.extensions import db
from app.models import Product
import json

app = create_app()


def seed_database():
    with app.app_context():
        # Limpa produtos antigos para não duplicar
        db.session.query(Product).delete()

        # --- DADOS PADRÃO (REPETEM EM QUASE TODOS) ---
        adicionais_padrao = [
            {"nome": "Hambúrguer", "price": 2.5},
            {"nome": "Hambúrguer Artesanal", "price": 5.0},
            {"nome": "Mussarela", "price": 3.0},
            {"nome": "Bacon", "price": 3.0},
            {"nome": "Salsicha", "price": 2.0},
            {"nome": "Ovo", "price": 2.0},
            {"nome": "Requeijão ou cheddar", "price": 2.0},
            {"nome": "Batata Palha", "price": 3.0},
        ]

        acompanhamentos_padrao = [
            {"nome": "Porção de batata porção inteira", "price": 30.0},
            {"nome": "Porção de batata porção 1/2", "price": 20.0},
            {"nome": "Bacon e cheddar porção inteira", "price": 40.0},
            {"nome": "Bacon e cheddar porção 1/2", "price": 30.0},
            {"nome": "Calabresa porção inteira", "price": 40.0},
            {"nome": "Calabresa porção 1/2", "price": 25.0},
        ]

        # --- LISTA DE PRODUTOS (BASEADA NO SEU API.JS) ---
        products_data = [
            # LANCHES
            {
                "name": "FALCÃO", "price": 30.0, "category": "Lanche",
                "description": "Pão, presunto, mussarela, ovo, requeijão, bacon, milho, alface, tomate. (Opções de Carnes: Frango, Lombo ou Filé)",
                "image_url": "assets/falcao.jpg",
                "details": {
                    "carnes": [{"nome": "Frango", "price": 0}, {"nome": "Lombo", "price": 0},
                               {"nome": "Filé", "price": 0}],
                    "acompanhamentos": acompanhamentos_padrao,
                    "adicionais": adicionais_padrao
                }
            },
            {
                "name": "ÁGUIA", "price": 35.0, "category": "Lanche",
                "description": "Pão, Hambúrguer da casa, duas fatias de presunto, Mussarela, ovo, Bacon, Cenoura, Milho, Alface, Tomate.",
                "image_url": "assets/aguia.jpg",
                "details": {
                    "carnes": [{"nome": "Hambúrguer", "price": 0}],
                    "acompanhamentos": acompanhamentos_padrao,
                    "adicionais": adicionais_padrao
                }
            },
            # ... (Você pode adicionar o resto da lista aqui seguindo o padrão) ...

            # COMBOS
            {
                "name": "COMBO CALOPSITA + BATATA FRITA", "price": 45.0, "category": "Combo",
                "description": "Pão, Hambúrguer, Presunto, Ovo, Salsicha, Bacon, Creme de Leite, Alface, Tomate, Milho + 250G de Batata Frita",
                "image_url": "assets/combo-calopsita.jpg",
                "details": {
                    "carnes": [],
                    "acompanhamentos": acompanhamentos_padrao,
                    "adicionais": adicionais_padrao
                }
            }
        ]

        print("Criando produtos...")
        for p_data in products_data:
            new_prod = Product(
                name=p_data['name'],
                description=p_data['description'],
                price=p_data['price'],
                image_url=p_data['image_url'],
                category=p_data['category'],
                is_available=True,
                # AQUI ESTÁ O SEGREDO: Convertemos o dicionário Python para String JSON
                details_json=json.dumps(p_data['details'])
            )
            db.session.add(new_prod)

        db.session.commit()
        print("Banco de dados populado com sucesso!")


if __name__ == '__main__':
    seed_database()