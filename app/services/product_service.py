from ..models import Product, db
from ..schemas import products_schema, product_schema
import json
from marshmallow import ValidationError


def get_all_products(only_available=True):
    """
    Busca produtos.
    Se only_available=True (Cliente), traz só os disponíveis.
    Se only_available=False (Admin), traz tudo.
    """
    if only_available:
        products = Product.query.filter_by(is_available=True).all()
    else:
        products = Product.query.all()

    return products_schema.dump(products)


def get_product_by_id(product_id):
    product = Product.query.get(product_id)
    if not product:
        raise ValueError("Produto não encontrado.")
    return product_schema.dump(product)


def get_products_by_category(category_name):
    products = Product.query.filter_by(is_available=True, category=category_name).all()
    return products_schema.dump(products)


def create_product(data):
    # Separa o 'details' (JSON) dos dados planos
    details_data = data.pop('details', {})

    try:
        new_product = product_schema.load(data, session=db.session)
        new_product.details_json = json.dumps(details_data)  # Salva manual

        db.session.add(new_product)
        db.session.commit()

        return product_schema.dump(new_product)
    except ValidationError as err:
        raise ValueError(err.messages)


def update_product(product_id, data):
    product = Product.query.get(product_id)
    if not product:
        raise ValueError("Produto não encontrado.")

    # Se vier 'details', tratamos separado
    if 'details' in data:
        details_data = data.pop('details')
        product.details_json = json.dumps(details_data)

    # Atualiza campos simples (name, price, description, etc)
    for key, value in data.items():
        if hasattr(product, key):
            setattr(product, key, value)

    try:
        db.session.commit()
        return product_schema.dump(product)
    except Exception as e:
        db.session.rollback()
        raise ValueError(f"Erro ao atualizar: {str(e)}")


def toggle_availability(product_id):
    """
    Interruptor rápido: Se tá On vira Off, se tá Off vira On.
    Útil para quando acaba um ingrediente na cozinha.
    """
    product = Product.query.get(product_id)
    if not product:
        raise ValueError("Produto não encontrado.")

    product.is_available = not product.is_available
    db.session.commit()

    return {"id": product.id, "is_available": product.is_available}


def delete_product(product_id):
    """
    Hard Delete. Cuidado: Se tiver pedidos com esse produto, pode dar erro de FK.
    Idealmente, num sistema grande, usaríamos Soft Delete (apenas desativar).
    """
    product = Product.query.get(product_id)
    if not product:
        raise ValueError("Produto não encontrado.")

    db.session.delete(product)
    db.session.commit()
    return True