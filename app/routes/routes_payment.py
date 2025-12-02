from flask import Blueprint, jsonify, request
from app import services
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.decorators import admin_required

bp_payment = Blueprint('payment', __name__)

# ==============================================================================
# 💳 ÁREA DO CLIENTE
# (Escolher forma de pagamento, Pagar Online)
# ==============================================================================

@bp_payment.route('/process', methods=['POST'])
@jwt_required()
def process_payment():
    """
    Cliente envia: { "order_id": 1, "payment_method": "card_machine" }
    """
    data = request.get_json()
    user_id = get_jwt_identity()

    try:
        result = services.payment_service.process_payment_logic(user_id, data)
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


# ==============================================================================
# 🤖 ÁREA EXTERNA (WEBHOOKS)
# (O Mercado Pago chama aqui. NÃO TEM LOGIN, pois é servidor-servidor)
# ==============================================================================

@bp_payment.route('/webhook/mercadopago', methods=['POST'])
@admin_required()
def webhook_mercadopago():
    data = request.get_json()
    # Chama o serviço sem bloquear a thread
    services.payment_service.process_webhook_logic(data)
    return jsonify({"status": "received"}), 200


# ==============================================================================
# 👨‍🍳 ÁREA DO RESTAURANTE (ADMIN)
# (Confirmar pagamento manual na volta do motoboy)
# ==============================================================================

@bp_payment.route('/<int:order_id>/confirm', methods=['PATCH'])
@admin_required()
def manual_confirm(order_id):
    """
    Motoboy voltou com o dinheiro? Admin clica em "Confirmar Pagamento".
    """
    try:
        order = services.payment_service.admin_confirm_payment_logic(order_id)
        return jsonify({'message': 'Pagamento confirmado manualmente.', 'order': order}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400