from flask import Blueprint, jsonify, request
from app.services import product_service
from flask_jwt_extended import jwt_required
from app.decorators import admin_required
from app.extensions import limiter
bp_menu = Blueprint('menu', __name__)

# --- ROTAS PÚBLICAS (CLIENTE) ---

@bp_menu.route('', methods=['GET'])
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def get_menu():
    # Cliente vê apenas os disponíveis
    products_list = product_service.get_all_products(only_available=True)
    return jsonify(products_list), 200

@bp_menu.route('/<int:product_id>', methods=['GET'])
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def get_product_details(product_id):
    try:
        product = product_service.get_product_by_id(product_id)
        return jsonify(product), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404

@bp_menu.route('/lanches', methods=['GET'])
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def get_lanches():
    return jsonify(product_service.get_products_by_category('Lanche'))

@bp_menu.route('/combos', methods=['GET'])
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def get_combos():
    return jsonify(product_service.get_products_by_category('Combo'))

# [NOVO] Adicione isto aqui:
@bp_menu.route('/bebidas', methods=['GET'])
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")

def get_bebidas():
    return jsonify(product_service.get_products_by_category('Bebida'))

# --- ROTAS PROTEGIDAS (RESTAURANTE/ADMIN) ---

# 1. Listar TUDO (Inclusive indisponíveis, para o Admin editar)
@bp_menu.route('/admin', methods=['GET'])
@admin_required()
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")

def get_admin_menu():
    products_list = product_service.get_all_products(only_available=False)
    return jsonify(products_list), 200

# 2. Criar Novo Produto
@bp_menu.route('', methods=['POST'])
@admin_required()
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")

def add_product():
    data = request.get_json()
    try:
        new_prod = product_service.create_product(data)
        return jsonify({'message': 'Produto criado!', 'product': new_prod}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

# 3. Editar Produto Existente
@bp_menu.route('/<int:product_id>', methods=['PUT'])
@admin_required()
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")

def edit_product(product_id):
    data = request.get_json()
    try:
        updated_prod = product_service.update_product(product_id, data)
        return jsonify({'message': 'Produto atualizado!', 'product': updated_prod}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

# 4. Pausar/Ativar Venda (Rápido)
@bp_menu.route('/<int:product_id>/toggle', methods=['PATCH'])
@admin_required()
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")

def toggle_product(product_id):
    try:
        result = product_service.toggle_availability(product_id)
        status = "Ativado" if result['is_available'] else "Pausado"
        return jsonify({'message': f'Produto {status}!', 'status': result}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404

# 5. Excluir Produto
@bp_menu.route('/<int:product_id>', methods=['DELETE'])
@admin_required()
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")

def remove_product(product_id):
    # Pega o corpo da requisição (onde virá a senha)
    data = request.get_json() or {}
    password = data.get('password')

    try:
        # Passa a senha para o serviço validar
        product_service.delete_product(product_id, password)
        return jsonify({'message': 'Produto removido com sucesso.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400


