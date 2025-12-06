# app/routes/routes_delivery.py
from flask import Blueprint, jsonify, request
from app.models import Neighborhood, db
from app.schemas import neighborhoods_schema, neighborhood_schema
from app.decorators import admin_required
from flask_jwt_extended import jwt_required, get_jwt_identity

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

    # Verifica duplicidade
    if Neighborhood.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Bairro já cadastrado'}), 400

    new_bairro = Neighborhood(
        name=data['name'],
        price=float(data['price']),
        is_active=True
    )
    db.session.add(new_bairro)
    db.session.commit()
    return jsonify(neighborhood_schema.dump(new_bairro)), 201


@bp_delivery.route('/<int:id>', methods=['PUT'])
@admin_required()
def update_neighborhood(id):
    bairro = Neighborhood.query.get(id)
    if not bairro: return jsonify({'error': 'Não encontrado'}), 404

    data = request.get_json()
    if 'name' in data: bairro.name = data['name']
    if 'price' in data: bairro.price = float(data['price'])
    if 'is_active' in data: bairro.is_active = data['is_active']

    db.session.commit()
    return jsonify(neighborhood_schema.dump(bairro)), 200


@bp_delivery.route('/<int:id>', methods=['DELETE'])
@admin_required()
def delete_neighborhood(id):
    bairro = Neighborhood.query.get(id)
    if bairro:
        db.session.delete(bairro)
        db.session.commit()
    return jsonify({'message': 'Deletado'}), 200