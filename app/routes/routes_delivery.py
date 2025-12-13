# app/routes/routes_delivery.py
from flask import Blueprint, jsonify, request
from app.models import Neighborhood, db
from app.schemas import neighborhoods_schema, neighborhood_schema
from app.decorators import admin_required
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services import delivery_service

bp_delivery = Blueprint('delivery', __name__)


# --- PÚBLICO (Para o Checkout) ---
@bp_delivery.route('', methods=['GET'])
def get_neighborhoods():
    # Retorna apenas os ativos para o cliente escolher
    bairros = Neighborhood.query.filter_by(is_active=True).order_by(Neighborhood.name).all()
    return jsonify(neighborhoods_schema.dump(bairros)), 200


# --- ADMIN (Gestão) ---
@bp_delivery.route('/admin', methods=['GET'])
@admin_required()
def get_all_neighborhoods():
    # Retorna todos (ativos e inativos) para gestão
    bairros = Neighborhood.query.order_by(Neighborhood.name).all()
    return jsonify(neighborhoods_schema.dump(bairros)), 200


@bp_delivery.route('', methods=['POST'])
@admin_required()
def add_neighborhood():
    data = request.get_json()
    try:
        new_bairro = delivery_service.adicionar_bairro(data)
        return jsonify(neighborhood_schema.dump(new_bairro)), 201
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception as e:
        # ERRO INESPERADO (Crash)
        return jsonify({"erro": "Erro interno do servidor"}), 500


@bp_delivery.route('/<int:id>', methods=['PUT'])
@admin_required()
def update_neighborhood(id):
    data = request.get_json()

    try:
        # Chama a lógica no service
        bairro_atualizado = delivery_service.atualizar_bairro_logic(id, data)
        return jsonify(neighborhood_schema.dump(bairro_atualizado)), 200

    except ValueError as e:
        msg_erro = str(e)
        # Se o erro for "não encontrado", retornamos 404. Se for validação, 400.
        if "não encontrado" in msg_erro:
            return jsonify({'error': msg_erro}), 404
        return jsonify({'error': msg_erro}), 400

    except Exception:
        return jsonify({'error': 'Erro interno do servidor'}), 500


@bp_delivery.route('/<int:id>', methods=['DELETE'])
@admin_required()
def delete_neighborhood(id):
    try:
        # Chama a lógica no service
        delivery_service.deletar_bairro_logic(id)
        return jsonify({'message': 'Deletado com sucesso'}), 200

    except ValueError as e:
        # Captura especificamente o erro de ID inexistente
        return jsonify({'error': str(e)}), 404

    except Exception:
        return jsonify({'error': 'Erro interno ao deletar'}), 500