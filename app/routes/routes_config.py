from flask import Blueprint, jsonify, request
from app.schemas import coupons_schema, coupon_schema, schedule_list_schema
from app.decorators import admin_required
from app.services import config_service # Importando o novo service
from app.extensions import limiter

bp_config = Blueprint('config', __name__)

# --- ROTAS DE CUPONS ---

@bp_config.route('/coupons/public', methods=['GET'])
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def list_public_coupons():
    """Rota pública para o carrinho verificar cupons disponíveis."""
    try:
        coupons = config_service.get_public_coupons_logic()
        return jsonify(coupons_schema.dump(coupons)), 200
    except Exception:
        return jsonify({'error': 'Erro ao buscar cupons'}), 500

@bp_config.route('/coupons', methods=['GET'])
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
@admin_required()
def list_coupons_admin():
    """Rota admin para ver todos os cupons."""
    try:
        coupons = config_service.get_all_coupons_logic()
        return jsonify(coupons_schema.dump(coupons)), 200
    except Exception:
        return jsonify({'error': 'Erro interno'}), 500

@bp_config.route('/coupons', methods=['POST'])
@admin_required()
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def create_coupon():
    data = request.get_json()
    try:
        new_coupon = config_service.create_coupon_logic(data)
        return jsonify(coupon_schema.dump(new_coupon)), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'Erro interno ao criar cupom'}), 500

@bp_config.route('/coupons/<int:id>', methods=['DELETE'])
@admin_required()
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def delete_coupon(id):
    try:
        config_service.delete_coupon_logic(id)
        return jsonify({'message': 'Cupom deletado com sucesso'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception:
        return jsonify({'error': 'Erro interno ao deletar'}), 500

# --- ROTAS DE HORÁRIO (SCHEDULE) ---

@bp_config.route('/schedule', methods=['GET'])
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def get_schedule():
    """Público: Retorna horários de funcionamento."""
    try:
        schedules = config_service.get_schedule_logic()
        return jsonify(schedule_list_schema.dump(schedules)), 200
    except Exception:
        return jsonify({'error': 'Erro ao buscar horários'}), 500

@bp_config.route('/schedule', methods=['PUT'])
@admin_required()
@limiter.limit("200 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def update_schedule():
    """Admin: Atualiza grade de horários."""
    data = request.get_json()
    try:
        config_service.update_schedule_logic(data)
        return jsonify({'message': 'Horários atualizados!'}), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception:
        return jsonify({'error': 'Erro interno ao atualizar horários'}), 500

# --- RELATÓRIO DE USUÁRIOS ---

@bp_config.route('/users', methods=['GET'])
@admin_required()
@limiter.limit("30 per hour", error_message="Muitas requisições, tente novamente mais tarde.")
def list_users_report():
    """
    Relatório de clientes + qtd de pedidos.
    Agora usa a versão otimizada do Service.
    """
    try:
        report_data = config_service.get_users_report_logic()
        # Como o service já retorna uma lista de dicionários (dict),
        # não precisamos usar o schema 'dump', podemos retornar direto.
        return jsonify(report_data), 200
    except Exception as e:
        print(f"Erro relatório usuários: {e}") # Log para debug
        return jsonify({'error': 'Erro ao gerar relatório de usuários'}), 500