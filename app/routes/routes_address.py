from flask import Blueprint, jsonify, request
from app.services import address_service
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import limiter
from app.decorators import verified_user_required
bp_address = Blueprint('address', __name__)

@bp_address.route('', methods=['GET'])
@jwt_required()
@limiter.limit('40 per hour')
def list_addresses():
    user_id = get_jwt_identity()
    return jsonify(address_service.get_user_addresses(user_id))

@bp_address.route('', methods=['POST'])
@jwt_required()
@verified_user_required()
@limiter.limit('20 per hour')
def add_address():
    user_id = get_jwt_identity()
    data = request.get_json()
    try:
        new_addr = address_service.add_address_logic(user_id, data)
        return jsonify(new_addr), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp_address.route('/<int:id>/active', methods=['PATCH'])
@jwt_required()
@verified_user_required()
@limiter.limit('30 per hour')
def set_active(id):
    user_id = get_jwt_identity()
    try:
        addr = address_service.set_active_address(user_id, id)
        return jsonify(addr), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@bp_address.route('/<int:id>', methods=['DELETE'])
@jwt_required()
@verified_user_required()
@limiter.limit('30 per hour')
def delete_addr(id):
    user_id = get_jwt_identity()
    try:
        address_service.delete_address(user_id, id)
        return jsonify({'message': 'Deletado'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400