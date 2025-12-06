from flask import Blueprint, jsonify, request
from app.models import Coupon, User, db
from app.schemas import coupons_schema, coupon_schema, admin_users_schema
from app.decorators import admin_required
from app.models import StoreSchedule
from app.schemas import schedule_list_schema

bp_config = Blueprint('config', __name__)


# --- CUPONS ---

# app/routes/routes_config.py

# ... (código existente) ...

# --- ROTA PÚBLICA (Para o Site do Cliente) ---
@bp_config.route('/coupons/public', methods=['GET'])
def list_public_coupons():
    # Busca apenas cupons ativos e que ainda não atingiram o limite
    from app.models import Coupon
    from app.extensions import db

    # Filtra cupons ativos
    coupons = Coupon.query.filter_by(is_active=True).all()

    # Filtra logicamente os que têm limite de uso (se usage_limit for definido)
    valid_coupons = [
        c for c in coupons
        if c.usage_limit is None or c.used_count < c.usage_limit
    ]

    return jsonify(coupons_schema.dump(valid_coupons)), 200

@bp_config.route('/schedule', methods=['GET'])
def get_schedule():
    # Rota PÚBLICA para o site saber se está aberto
    schedules = StoreSchedule.query.order_by(StoreSchedule.day_of_week).all()
    return jsonify(schedule_list_schema.dump(schedules)), 200

@bp_config.route('/coupons', methods=['GET'])
@admin_required()
def list_coupons():
    coupons = Coupon.query.all()
    return jsonify(coupons_schema.dump(coupons)), 200


@bp_config.route('/coupons', methods=['POST'])
@admin_required()
def create_coupon():
    data = request.get_json()

    # Validação simples
    if Coupon.query.filter_by(code=data['code']).first():
        return jsonify({'error': 'Código já existe'}), 400

    new_coupon = Coupon(
        code=data['code'].upper(),
        discount_percent=data.get('discount_percent', 0),
        discount_fixed=data.get('discount_fixed', 0.0),
        min_purchase=data.get('min_purchase', 0.0),
        usage_limit=data.get('usage_limit'),
        is_active=True
    )
    db.session.add(new_coupon)
    db.session.commit()
    return jsonify(coupon_schema.dump(new_coupon)), 201


@bp_config.route('/coupons/<int:id>', methods=['DELETE'])
@admin_required()
def delete_coupon(id):
    c = Coupon.query.get(id)
    if c:
        db.session.delete(c)
        db.session.commit()
        return jsonify({'message': 'Deletado'}), 200
    return jsonify({'error': 'Não encontrado'}), 404


@bp_config.route('/schedule', methods=['PUT'])
@admin_required()
def update_schedule():
    # Recebe uma lista de dias para atualizar
    data = request.get_json()  # Espera uma lista: [{day_of_week: 0, open_time: ...}, ...]

    try:
        for item in data:
            day = StoreSchedule.query.filter_by(day_of_week=item['day_of_week']).first()
            if day:
                day.open_time = item.get('open_time', day.open_time)
                day.close_time = item.get('close_time', day.close_time)
                day.is_closed = item.get('is_closed', day.is_closed)

        db.session.commit()
        return jsonify({'message': 'Horários atualizados!'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# --- USUÁRIOS (Relatório) ---

@bp_config.route('/users', methods=['GET'])
@admin_required()
def list_users_report():
    # Lista apenas clientes, não admins
    users = User.query.filter(User.role != 'super_admin').all()

    # Adiciona contagem de pedidos manual (ou via query complexa)
    result = []
    for u in users:
        user_dict = {
            "id": u.id,
            "name": u.name,
            "whatsapp": u.whatsapp,
            "email": u.email,
            "role": u.role,
            "orders_count": len(u.orders)  # Conta pedidos
        }
        result.append(user_dict)

    return jsonify(result), 200