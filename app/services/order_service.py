from ..models import Order, OrderItem, Product, db, Neighborhood, Coupon
import json
from ..schemas import orders_schema
from sqlalchemy.orm import joinedload
from datetime import datetime, time
from sqlalchemy import desc  # <--- FALTAVA ISTO
from decimal import Decimal # [IMPORTANTE] Importar Decimal
from ..extensions import socketio # <--- Importe o socketio


def create_order_logic(data, user_id=None):
    # 1. Validação e Cabeçalho
    customer_data = data.get('customer', {})
    address_data = customer_data.get('address', {})
    payment_method_chosen = data.get('payment_method', 'Não informado')
    coupon_code = data.get('coupon_code')

    if not address_data.get('street') and address_data.get('street') != 'RETIRADA NO LOCAL':
        # Se for retirada, o front manda "RETIRADA NO LOCAL", então passa.
        # Se for entrega e vier vazio, bloqueia.
        if not address_data.get('street'):
            raise ValueError("Endereço obrigatório.")

    # 1.1 Recupera Taxa de Entrega
    neighborhood_name = address_data.get('neighborhood')
    delivery_fee = Decimal('0.00')

    if neighborhood_name and neighborhood_name != "-":
        bairro_db = Neighborhood.query.filter_by(name=neighborhood_name).first()
        if bairro_db:
            delivery_fee = bairro_db.price

    new_order = Order(
        user_id=user_id,
        status='Recebido',
        total_price=Decimal('0.00'),
        delivery_fee=delivery_fee,
        payment_method=payment_method_chosen,
        payment_status='pending',
        customer_name=customer_data.get('name'),
        customer_phone=customer_data.get('phone'),
        street=address_data.get('street'),
        number=address_data.get('number'),
        neighborhood=address_data.get('neighborhood'),
        complement=address_data.get('complement')
    )

    db.session.add(new_order)
    db.session.flush()

    # 2. Processamento dos Itens
    items_list = data.get('items', [])
    total_order_value = Decimal('0.00')

    if not items_list:
        raise ValueError("O pedido deve conter pelo menos um item.")

    for item_data in items_list:
        product = Product.query.with_for_update().get(item_data['product_id'])
        if not product:
            raise ValueError(f"Produto ID {item_data['product_id']} não encontrado.")

        # Lógica de Estoque
        if product.stock_quantity is not None:
            if product.stock_quantity < item_data['quantity']:
                raise ValueError(f"Estoque insuficiente para '{product.name}'. Restam {product.stock_quantity}.")
            product.stock_quantity -= item_data['quantity']
            if product.stock_quantity <= 0:
                product.is_available = False

        customizations = item_data.get('customizations', {})
        final_price = _calculate_item_price(product, customizations)

        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=item_data['quantity'],
            price_at_time=final_price,
            customizations_json=json.dumps(customizations)
        )
        db.session.add(order_item)
        total_order_value += (final_price * item_data['quantity'])

    # Soma Frete
    total_order_value += delivery_fee

    # 3. Cupom
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        if not coupon:
            raise ValueError(f"Cupom '{coupon_code}' inválido.")

        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            raise ValueError("Cupom esgotado.")
        min_purchase = Decimal(str(coupon.min_purchase))
        # O front já validou o mínimo, mas validamos aqui também (subtraindo o frete para ser justo ou não, depende da regra. Vamos validar no total bruto).
        if total_order_value < coupon.min_purchase:
            raise ValueError(f"Valor mínimo não atingido para o cupom.")

        discount = Decimal('0.00')

        if coupon.discount_percent:
            percent = Decimal(str(coupon.discount_percent))
            discount = total_order_value * (percent / 100)
        elif coupon.discount_fixed:
            discount = Decimal(str(coupon.discount_fixed))

        total_order_value = max(Decimal('0.00'), total_order_value - discount)
        coupon.used_count += 1

    # 4. Finalização
    new_order.total_price = total_order_value
    db.session.commit()

    # Integração MP
    result_dump = orders_schema.dump([new_order])[0]

    # if payment_method_chosen == 'mercadopago':
    #     from app.services import payment_service
    #     pay_data = {"order_id": new_order.id, "payment_method": "mercadopago"}
    #     # Aqui o payment_service pode retornar dict com redirect_url
    #     payment_resp = payment_service.process_payment_logic(user_id, pay_data)
    #     if payment_resp and 'redirect_url' in payment_resp:
    #         result_dump['redirect_url'] = payment_resp['redirect_url']

    print(f"📡 Emitindo evento novo_pedido para ID: {new_order.id}")
    socketio.emit('novo_pedido', convert_decimals(result_dump))

    return result_dump


def get_order_logic(user_id):
    orders = Order.query.options(joinedload(Order.items)) \
        .filter_by(user_id=user_id) \
        .order_by(Order.date_created.desc()) \
        .all()
    return orders_schema.dump(orders)


# [NOVA FUNÇÃO DE FILTRO]
def get_filtered_orders(filters):
    query = Order.query.options(joinedload(Order.items))

    # 1. Filtro por ID
    if filters.get('order_id') and filters['order_id'] != '':
        query = query.filter(Order.id == filters['order_id'])

    else:
        # 2. Filtro por Data
        if filters.get('start_date'):
            try:
                start = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                query = query.filter(Order.date_created >= start)
            except:
                pass  # Se data inválida, ignora

        if filters.get('end_date'):
            try:
                end = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                end = end.replace(hour=23, minute=59, second=59)
                query = query.filter(Order.date_created <= end)
            except:
                pass

        # 3. Nome
        if filters.get('customer_name'):
            query = query.filter(Order.customer_name.ilike(f"%{filters['customer_name']}%"))

        # 4. Pagamento
        if filters.get('payment_method'):
            query = query.filter(Order.payment_method == filters['payment_method'])

    # Ordena mais recente primeiro
    orders = query.order_by(desc(Order.date_created)).all()
    return orders_schema.dump(orders)


# --- FUNÇÕES AUXILIARES ---

def _calculate_item_price(product, customizations):
    base_price = product.price
    details = product.get_details()

    # Soma listas
    for tipo in ['adicionais', 'acompanhamentos', 'bebidas']:
        escolhidos = customizations.get(tipo, [])
        disponiveis = details.get(tipo, [])
        for esc in escolhidos:
            match = next((Op for Op in disponiveis if Op['nome'] == esc), None)
            if match:
                preco_adicional = Decimal(str(match['price']))
                base_price += preco_adicional

    return base_price


def update_order_status_logic(order_id, new_status):
    ALLOWED = ["Recebido", "Em Preparo", "Saiu para Entrega", "Concluído", "Cancelado"]
    if new_status not in ALLOWED: raise ValueError("Status inválido")

    order = Order.query.get(order_id)
    if not order: raise ValueError("Pedido não encontrado")

    order.status = new_status
    db.session.commit()

    order_data = orders_schema.dump([order])[0]

    # [NOVO] Emite o evento de atualização
    print(f"📡 Status do Pedido #{order.id} mudou para {new_status}")
    payload = {
        'order_id': order.id,
        'status': new_status,
        'user_id': order.user_id,
        'order_data': order_data
    }
    socketio.emit('status_update', convert_decimals(payload))

    return orders_schema.dump([order])[0]


def get_order_status_logic(order_id):
    order = Order.query.get(order_id)
    if not order: raise ValueError("Pedido não encontrado")
    return {"id": order.id, "status": order.status}


def cancel_order_by_client_logic(order_id, user_id):
    order = Order.query.get(order_id)
    if not order: raise ValueError("Pedido não encontrado")
    if str(order.user_id) != str(user_id): raise ValueError("Não autorizado")
    if order.status != 'Recebido': raise ValueError("Já em preparo")

    order.status = 'Cancelado'
    db.session.commit()
    return order


def soft_delete_order_by_admin_logic(order_id):
    order = Order.query.get(order_id)
    if not order: raise ValueError("Pedido não encontrado")
    order.status = 'Cancelado'
    db.session.commit()
    return order


# Mantivemos para compatibilidade, caso algum lugar chame, mas redireciona para o filtro vazio
def get_all_orders_daily():
    return get_filtered_orders({})


# Função auxiliar para limpar Decimals para o SocketIO
def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj) # Converte Decimal para Float
    return obj