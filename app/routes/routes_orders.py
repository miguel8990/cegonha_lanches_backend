from flask import Blueprint, jsonify, request
from app.services import order_service
from flask_jwt_extended import jwt_required, get_jwt_identity

# from flask_jwt_extended import get_jwt_identity # (Futuro auth)

bp_orders = Blueprint('orders', __name__)


@bp_orders.route('/', methods=['POST'])
@jwt_required()
def create_order():
    data = request.get_json()
    # user_id = get_jwt_identity() # Pegaria do token se tivesse logado
    user_id = get_jwt_identity()

    order = order_service.create_order_logic(data, user_id=user_id)

    return jsonify({'message': 'Pedido recebido!', 'order_id': order.id}), 201