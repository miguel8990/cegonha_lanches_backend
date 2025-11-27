from ..models import Product, db
from ..schemas import products_schema, product_schema
import json
from marshmallow import ValidationError


def get_all_products():
    # Busca produtos disponíveis
    products = Product.query.filter_by(is_available=True).all()
    # O Schema converte a lista de objetos do banco para JSON automaticamente
    return products_schema.dump(products)

def create_product(data):
    try:
        # 1. O Schema valida e cria o objeto Product automaticamente!
        # Se faltar preço ou vier tipo errado, ele pula pro 'except'
        new_product = product_schema.load(data, session=db.session)

        # 2. Ajuste manual: Converter o dicionário 'details' para texto JSON
        # O Schema espera os campos do banco, mas se o front mandar 'details',
        # tratamos aqui antes de salvar.
        if 'details' in data:
            new_product.details_json = json.dumps(data['details'])

        # 3. Salva no banco
        db.session.add(new_product)
        db.session.commit()

        # Retorna o produto criado formatado em JSON
        return product_schema.dump(new_product)

    except ValidationError as err:
        # Se o Schema encontrar erro (ex: preço negativo, falta nome),
        # ele captura aqui e mostramos a mensagem exata.
        raise ValueError(err.messages)


def get_products_by_category(category_name):
    # Busca por categoria (Lanche ou Combo)
    products = Product.query.filter_by(is_available=True, category=category_name).all()
    return products_schema.dump(products)