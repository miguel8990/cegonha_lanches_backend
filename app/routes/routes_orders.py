from flask import Blueprint, jsonify, request
from app import services
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.schemas import order_schema
from ..decorators import admin_required
from datetime import datetime  # <--- FALTAVA ISTO

bp_orders = Blueprint('orders', __name__)


# ==============================================================================
# 📱 ÁREA DO CLIENTE
# ==============================================================================

@bp_orders.route('/create', methods=['POST'])
@jwt_required()
def create_order():
    data = request.get_json()
    user_id = get_jwt_identity()
    # Validação extra de segurança: Garante que user_id existe
    if not user_id:
        return jsonify({'error': 'Usuário não autenticado.'}), 401

    try:
        result = services.order_service.create_order_logic(data, user_id=user_id)
        # Se for dict (MP), retorna direto. Se for objeto, faz dump.
        if isinstance(result, dict):
            return jsonify(result), 201
        return jsonify(order_schema.dump(result)), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@bp_orders.route('/me', methods=['GET'])
@jwt_required()
def get_my_order():
    user_id = get_jwt_identity()
    order = services.order_service.get_order_logic(user_id)
    return jsonify(order), 200


@bp_orders.route('/<int:order_id>/status', methods=['GET'])
def check_order_status(order_id):
    try:
        status_info = services.order_service.get_order_status_logic(order_id)
        return jsonify(status_info), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404


@bp_orders.route('/<int:order_id>/cancel', methods=['PATCH'])
@jwt_required()
def cancel_order(order_id):
    user_id = get_jwt_identity()
    try:
        services.order_service.cancel_order_by_client_logic(order_id, user_id)
        return jsonify({'message': 'Pedido cancelado com sucesso.'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ==============================================================================
# 👨‍🍳 ÁREA DO RESTAURANTE (ADMIN)
# ==============================================================================

@bp_orders.route('/admin', methods=['GET'])
@admin_required()
def order_for_kitchen():
    """
    Busca pedidos com filtros (Data, Nome, ID, etc).
    """
    # Coleta parametros da URL (?start_date=...&name=...)
    # Se vier vazio, é None
    filters = {
        'start_date': request.args.get('start_date'),
        'end_date': request.args.get('end_date'),
        'customer_name': request.args.get('customer_name'),
        'payment_method': request.args.get('payment_method'),
        'order_id': request.args.get('order_id')
    }

    # [CORREÇÃO]: Removi o bloco que forçava "Hoje" se viesse vazio.
    # Agora, se 'start_date' for vazio, o serviço busca tudo (Histórico Completo).

    try:
        orders = services.order_service.get_filtered_orders(filters)
        return jsonify(orders), 200
    except Exception as e:
        print(f"Erro ao filtrar pedidos: {str(e)}")  # Log no terminal para debug
        return jsonify({'error': str(e)}), 500


@bp_orders.route('/<int:order_id>/status', methods=['PATCH'])
@admin_required()
def update_status(order_id):
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
    try:
        updated_order = services.order_service.soft_delete_order_by_admin_logic(order_id)
        return jsonify({
            'message': 'Pedido cancelado e arquivado com sucesso (Soft Delete).',
            'order': services.order_service.orders_schema.dump([updated_order])[0]
        }), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404