from flask import Blueprint, jsonify, request
from app import services
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.schemas import order_schema
from ..decorators import admin_required

bp_orders = Blueprint('orders', __name__)

# ==============================================================================
# 📱 ÁREA DO CLIENTE
# (Criar, Listar Próprios, Ver Status, Cancelar)
# ==============================================================================

@bp_orders.route('/create', methods=['POST'])
@jwt_required()
def create_order():
    """
    Cliente cria um novo pedido.
    """
    data = request.get_json()
    user_id = get_jwt_identity()

    try:
        order = services.order_service.create_order_logic(data, user_id=user_id)
        # Retorna o pedido completo (com preços calculados)
        return jsonify(order_schema.dump(order)), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp_orders.route('/me', methods=['GET'])
@jwt_required()
def get_my_order():
    """
    Cliente vê lista dos seus próprios pedidos.
    """
    user_id = get_jwt_identity()
    order = services.order_service.get_order_logic(user_id)
    return jsonify(order), 200


@bp_orders.route('/<int:order_id>/status', methods=['GET'])
# @jwt_required() # Opcional: descomente se quiser exigir login
def check_order_status(order_id):
    """
    Rota leve para Polling (App chama a cada 30s para atualizar status).
    """
    try:
        status_info = services.order_service.get_order_status_logic(order_id)
        return jsonify(status_info), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@bp_orders.route('/<int:order_id>/cancel', methods=['PATCH'])
@jwt_required()
def cancel_order(order_id):
    """
    Cliente cancela o próprio pedido (se ainda estiver 'Recebido').
    """
    user_id = get_jwt_identity()
    try:
        services.order_service.cancel_order_by_client_logic(order_id, user_id)
        return jsonify({'message': 'Pedido cancelado com sucesso.'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ==============================================================================
# 👨‍🍳 ÁREA DO RESTAURANTE (ADMIN)
# (Painel da Cozinha, Atualizar Status, Arquivar/Deletar)
# ==============================================================================

@bp_orders.route('/admin', methods=['GET'])
@admin_required()
def order_for_kitchen():
    """
    Cozinha vê todos os pedidos do dia (Painel).
    """
    orders = services.order_service.get_all_orders_daily()
    return jsonify(orders), 200


@bp_orders.route('/<int:order_id>/status', methods=['PATCH'])
@admin_required()
def update_status(order_id):
    """
    Cozinha avança o status (ex: 'Em Preparo', 'Saiu para Entrega').
    """
    data = request.get_json()
    new_status = data.get('status')

    try:
        updated_order = services.order_service.update_order_status_logic(order_id, new_status)
        return jsonify({'message': 'Status atualizado!', 'order': updated_order}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp_orders.route('/<int:order_id>', methods=['DELETE'])
@admin_required()
def cancel_order_restaurante(order_id):
    """
    Gerente cancela/arquiva pedido problemático (Soft Delete).
    """
    try:
        updated_order = services.order_service.soft_delete_order_by_admin_logic(order_id)
        return jsonify({
            'message': 'Pedido cancelado e arquivado com sucesso (Soft Delete).',
            'order': services.order_service.orders_schema.dump([updated_order])[0]
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404