from flask import Blueprint, jsonify, request
from app.models import Order, db
from app.decorators import admin_required
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from decimal import Decimal

bp_reports = Blueprint('reports', __name__)


@bp_reports.route('/dashboard', methods=['GET'])
@admin_required()
def get_dashboard_stats():
    # 1. Captura filtros da URL
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    payment_method = request.args.get('payment_method')

    # 2. Define datas padrão (Se não vier nada, pega os últimos 30 dias)
    if not start_date_str:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
    else:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            # Se tem data fim, usa. Se não, assume que é só um dia (start = end)
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = end_date.replace(hour=23, minute=59, second=59)
            else:
                end_date = start_date.replace(hour=23, minute=59, second=59)
        except ValueError:
            return jsonify({'error': 'Formato de data inválido'}), 400

    # 3. Query Base (Apenas pedidos CONCLUÍDOS contam como receita real)
    query = db.session.query(Order).filter(Order.status == 'Concluído')

    # Aplica filtro de data
    query = query.filter(Order.date_created >= start_date)
    query = query.filter(Order.date_created <= end_date)

    # Aplica filtro de pagamento (se houver)
    if payment_method:
        query = query.filter(Order.payment_method == payment_method)

    # Executa a busca
    orders = query.order_by(Order.date_created).all()

    # 4. Processamento dos Dados (Agregação)
    total_faturado = db.session.query(func.sum(Order.total_price)) \
                         .filter(Order.status == 'Concluído') \
                         .filter(Order.date_created.between(start_date, end_date)) \
                         .scalar() or 0.0  # scalar pega o valor único

    # 2. Contagem Total
    total_pedidos = db.session.query(func.count(Order.id)) \
                        .filter(Order.status == 'Concluído') \
                        .filter(Order.date_created.between(start_date, end_date)) \
                        .scalar() or 0

    # 3. Gráfico (Agrupado por Dia no SQL)
    # Isso evita trazer milhares de linhas para o Python
    # (Sintaxe para SQLite/Postgres pode variar um pouco na extração de data,
    #  abaixo um exemplo genérico compatível com a maioria via func.date)
    stats_by_day = db.session.query(
        func.date(Order.date_created),
        func.sum(Order.total_price)
    ).filter(
        Order.status == 'Concluído',
        Order.date_created.between(start_date, end_date)
    ).group_by(func.date(Order.date_created)).all()

    # Monta o JSON
    labels = [str(day) for day, _ in stats_by_day]
    data_values = [float(amount) for _, amount in stats_by_day]

    return jsonify({
        "total_periodo": float(total_faturado),
        "qtd_pedidos": total_pedidos,
        "grafico": {"labels": labels, "data": data_values},
        "periodo_info": "..."
    }), 200


# Rota para o Dossiê (Continua igual, mas precisa estar aqui)
@bp_reports.route('/dossier/<int:order_id>', methods=['GET'])
@admin_required()
def get_order_dossier(order_id):
    order = Order.query.get(order_id)
    if not order: return jsonify({'error': 'Pedido não encontrado'}), 404

    from app.schemas import order_schema
    dump = order_schema.dump(order)

    dump['audit_info'] = {
        "created_at_iso": order.date_created.isoformat(),
        "payment_status_raw": order.payment_status,
        "is_delivery": order.street != "RETIRADA NO LOCAL"
    }

    return jsonify(dump), 200