from flask import Blueprint, jsonify, request
from app.services import payment_service
from flask_jwt_extended import jwt_required

bp_payment = Blueprint('payment', __name__)


@bp_payment.route('/webhook', methods=['POST'])
@jwt_required()
def payment_webhook():
    data = request.get_json()

    # Passa o JSON inteiro para o serviço resolver
    response, status_code = payment_service.process_webhook(data)

    return jsonify(response), status_code