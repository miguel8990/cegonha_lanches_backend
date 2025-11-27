from flask import Blueprint, jsonify, request
from app.services import product_service  # Importamos o nosso novo service
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User
bp_menu = Blueprint('menu', __name__)


@bp_menu.route('', methods=['GET'])
def get_menu():
    # A rota não sabe nada de banco de dados, só chama o serviço
    products_list = product_service.get_all_products()
    return jsonify(products_list), 200


@bp_menu.route('/', methods=['POST'])
@jwt_required()
def add_item():
    user_id = get_jwt_identity()
    current_user = User.query.get(user_id)
    if not current_user or not current_user.is_admin:
        return jsonify({'error': 'Operação permitida apenas para administradores.'}), 403



    data = request.get_json()

    try:
        # Passamos os dados para o service resolver
        new_prod = product_service.create_product(data)
        return jsonify({'message': 'Lanche criado!', 'id': new_prod.id}), 201
    except ValueError as e:
        # Se o service reclamar de algo (ex: preço negativo), devolvemos erro 400
        return jsonify({'error': str(e)}), 400

@bp_menu.route('/lanches', methods=['GET'])
def get_lanches():
    return jsonify(product_service.get_products_by_category('Lanche'))

@bp_menu.route('/combos', methods=['GET'])
def get_combos():
    return jsonify(product_service.get_products_by_category('Combo'))