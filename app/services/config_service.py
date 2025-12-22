from app.models import Coupon, StoreSchedule, User, Order, db
from sqlalchemy import func


def get_public_coupons_logic():
    """
    Retorna cupons válidos para o cliente.
    Regra: Ativo E (Sem limite OU limite não atingido).
    """
    coupons = Coupon.query.filter_by(is_active=True).all()

    # Filtra logicamente no Python os que têm limite de uso
    valid_coupons = [
        c for c in coupons
        if c.usage_limit is None or c.used_count < c.usage_limit
    ]
    return valid_coupons


def get_all_coupons_logic():
    """Retorna todos os cupons (para o Admin)."""
    return Coupon.query.all()


def create_coupon_logic(data):
    """
    Cria um novo cupom.
    """
    code = data.get('code', '').upper().strip()

    if not code:
        raise ValueError("O código do cupom é obrigatório.")

    if Coupon.query.filter_by(code=code).first():
        raise ValueError("Este código de cupom já existe.")

    new_coupon = Coupon(
        code=code,
        discount_percent=data.get('discount_percent', 0),
        discount_fixed=data.get('discount_fixed', 0.0),
        min_purchase=data.get('min_purchase', 0.0),
        usage_limit=data.get('usage_limit'),  # Pode ser None
        is_active=True
    )

    try:
        db.session.add(new_coupon)
        db.session.commit()
        return new_coupon
    except Exception:
        db.session.rollback()
        raise ValueError("Erro ao salvar cupom no banco.")


def delete_coupon_logic(coupon_id):
    """Remove um cupom."""
    coupon = Coupon.query.get(coupon_id)
    if not coupon:
        raise ValueError("Cupom não encontrado.")

    try:
        db.session.delete(coupon)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise ValueError("Erro ao deletar cupom.")


def get_schedule_logic():
    """Retorna a agenda ordenada por dia da semana."""
    return StoreSchedule.query.order_by(StoreSchedule.day_of_week).all()


def update_schedule_logic(data_list):
    """
    Atualiza horários em lote.
    Recebe uma lista de dicionários: [{day_of_week: 0, open_time: ...}, ...]
    """
    if not isinstance(data_list, list):
        raise ValueError("Formato inválido. Esperada uma lista de horários.")

    try:
        for item in data_list:
            day_idx = item.get('day_of_week')
            day_schedule = StoreSchedule.query.filter_by(day_of_week=day_idx).first()

            if day_schedule:
                # Atualiza apenas se o campo foi enviado
                if 'open_time' in item: day_schedule.open_time = item['open_time']
                if 'close_time' in item: day_schedule.close_time = item['close_time']
                if 'is_closed' in item: day_schedule.is_closed = item['is_closed']

        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        raise ValueError("Erro ao atualizar horários.")


def get_users_report_logic():
    """
    Gera relatório de usuários com contagem de pedidos.
    OTIMIZAÇÃO: Usa SQL puro (JOIN) em vez de loop Python para performance.
    """
    # Query: Seleciona Usuário e conta quantos pedidos ele tem
    results = db.session.query(
        User,
        func.count(Order.id).label('total_orders')
    ).outerjoin(Order).filter(User.role != 'super_admin').group_by(User.id).all()

    # Formata a saída para lista de dicionários
    output = []
    for user, count in results:
        output.append({
            
            "name": user.name,
            "whatsapp": user.whatsapp,
            "orders_count": count  # Dado vindo do Count SQL
        })

    return output


def get_users_for_delete():
    """
    Gera relatório de usuários com contagem de pedidos.
    OTIMIZAÇÃO: Usa SQL puro (JOIN) em vez de loop Python para performance.
    """
    # Query: Seleciona Usuário e conta quantos pedidos ele tem
    results = db.session.query(
        User,
        func.count(Order.id).label('total_orders')
    ).outerjoin(Order).filter(User.role != 'super_admin').group_by(User.id).all()

    # Formata a saída para lista de dicionários
    output = []
    for user, count in results:
        output.append({
            "id": user.id,          # <--- ADICIONADO: Obrigatório para a exclusão
            "name": user.name,
            "email": user.email,    # <--- ADICIONADO: Bom para conferência
            "whatsapp": user.whatsapp,
            "role": user.role,
            "orders_count": count
        })
    return output