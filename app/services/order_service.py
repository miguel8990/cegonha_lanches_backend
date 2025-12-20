from ..models import Order, OrderItem, Product, db, Neighborhood, Coupon
import json
from ..schemas import orders_schema
from sqlalchemy.orm import joinedload
from datetime import datetime
from sqlalchemy import desc
from decimal import Decimal, InvalidOperation  # Importe InvalidOperation
from ..extensions import socketio


def create_order_logic(data, user_id=None):
    print("\n--- INICIANDO CRIAÇÃO DE PEDIDO ---")

    # 1. Validação e Cabeçalho
    customer_data = data.get('customer', {})
    address_data = customer_data.get('address', {})
    payment_method_chosen = data.get('payment_method', 'Não informado')
    coupon_code = data.get('coupon_code')

    # Validação de Endereço
    if not address_data.get('street') and address_data.get('street') != 'RETIRADA NO LOCAL':
        if not address_data.get('street'):
            raise ValueError("Endereço obrigatório.")

    # 1.1 Recupera Taxa de Entrega (Blindagem Decimal)
    neighborhood_name = address_data.get('neighborhood')
    delivery_fee = Decimal('0.00')

    if neighborhood_name and neighborhood_name != "-":
        bairro_db = Neighborhood.query.filter_by(name=neighborhood_name).first()
        if bairro_db and bairro_db.price is not None:
            # Converte explicitamente para string antes de Decimal para evitar erros de precisão float
            delivery_fee = Decimal(str(bairro_db.price))

    print(f"💰 Taxa de Entrega Calculada: R$ {delivery_fee}")

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
    if not items_list:
        raise ValueError("O pedido deve conter pelo menos um item.")

    subtotal_produtos = Decimal('0.00')  # Variável para soma segura

    for item_data in items_list:
        product = Product.query.with_for_update().get(item_data['product_id'])
        if not product:
            raise ValueError(f"Produto ID {item_data['product_id']} não encontrado.")

        # Lógica de Estoque
        quantity = int(item_data['quantity'])  # Garante Inteiro

        if product.stock_quantity is not None:
            if product.stock_quantity < quantity:
                raise ValueError(f"Estoque insuficiente para '{product.name}'. Restam {product.stock_quantity}.")
            product.stock_quantity -= quantity
            if product.stock_quantity <= 0:
                product.is_available = False

        customizations = item_data.get('customizations', {})

        # Calcula preço unitário (Blindado)
        unit_price = _calculate_item_price(product, customizations)

        # Calcula total da linha
        line_total = unit_price * quantity

        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=quantity,
            price_at_time=unit_price,
            customizations_json=json.dumps(customizations)
        )
        db.session.add(order_item)
        subtotal_produtos += line_total

    print(f"🛒 Subtotal Produtos: R$ {subtotal_produtos}")

    # 3. Cupom (Lógica corrigida e debugada)
    discount = Decimal('0.00')

    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()
        if not coupon:
            raise ValueError(f"Cupom '{coupon_code}' inválido.")

        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            raise ValueError("Cupom esgotado.")

        # Validação de Mínimo
        if coupon.min_purchase is not None:
            min_purchase = Decimal(str(coupon.min_purchase))

            # REGRA DE OURO: A validação do mínimo deve ser sobre os PRODUTOS (Subtotal),
            # não sobre o total com frete. Isso evita confusão.
            # Se você preferir validar sobre o Total Geral, troque 'subtotal_produtos' por 'subtotal_produtos + delivery_fee'
            valor_para_validar = subtotal_produtos

            print(f"🎫 Validando Cupom: Mínimo R$ {min_purchase} | Valor Pedido R$ {valor_para_validar}")

            if valor_para_validar < min_purchase:
                raise ValueError(
                    f"O valor mínimo para este cupom é R$ {min_purchase}. Faltam R$ {min_purchase - valor_para_validar}.")

        # Cálculo do Desconto
        # O desconto incide sobre os PRODUTOS (não sobre o frete, geralmente)
        base_calculo = subtotal_produtos

        if coupon.discount_percent:
            percent = Decimal(str(coupon.discount_percent))
            discount = base_calculo * (percent / 100)
        elif coupon.discount_fixed:
            discount = Decimal(str(coupon.discount_fixed))

        # Garante que desconto não exceda o valor dos produtos
        if discount > base_calculo:
            discount = base_calculo

        coupon.used_count += 1
        print(f"🎫 Desconto Aplicado: R$ {discount}")

    # 4. Finalização (Total Geral = Produtos + Frete - Desconto)
    total_order_value = subtotal_produtos + delivery_fee - discount
    # Garante que não fique negativo (caso raro)
    total_order_value = max(Decimal('0.00'), total_order_value)

    print(f"💰 TOTAL FINAL: R$ {total_order_value}")

    new_order.total_price = total_order_value
    db.session.commit()

    # Integração MP e SocketIO
    result_dump = orders_schema.dump([new_order])[0]

    print(f"📡 Emitindo evento novo_pedido para ID: {new_order.id}")
    socketio.emit('novo_pedido', convert_decimals(result_dump))

    return result_dump


def get_order_logic(user_id):
    orders = Order.query.options(joinedload(Order.items)) \
        .filter_by(user_id=user_id) \
        .order_by(Order.date_created.desc()) \
        .all()
    return orders_schema.dump(orders)


def get_filtered_orders(filters):
    query = Order.query.options(joinedload(Order.items))

    if filters.get('order_id') and filters['order_id'] != '':
        query = query.filter(Order.id == filters['order_id'])
    else:
        if filters.get('start_date'):
            try:
                start = datetime.strptime(filters['start_date'], '%Y-%m-%d')
                query = query.filter(Order.date_created >= start)
            except:
                pass

        if filters.get('end_date'):
            try:
                end = datetime.strptime(filters['end_date'], '%Y-%m-%d')
                end = end.replace(hour=23, minute=59, second=59)
                query = query.filter(Order.date_created <= end)
            except:
                pass

        if filters.get('customer_name'):
            query = query.filter(Order.customer_name.ilike(f"%{filters['customer_name']}%"))

        if filters.get('payment_method'):
            query = query.filter(Order.payment_method == filters['payment_method'])

    orders = query.order_by(desc(Order.date_created)).all()
    return orders_schema.dump(orders)


# --- FUNÇÕES AUXILIARES BLINDADAS ---

def _calculate_item_price(product, customizations):
    """
    Calcula o preço do item garantindo que tudo seja DECIMAL.
    Evita erro de Float + Decimal.
    """
    # 1. Preço Base (Converte Float do banco para Decimal)
    try:
        base_price = Decimal(str(product.price))
    except:
        base_price = Decimal('0.00')

    details = product.get_details()

    # 2. Soma Adicionais
    for tipo in ['adicionais', 'acompanhamentos', 'bebidas']:
        escolhidos = customizations.get(tipo, [])
        disponiveis = details.get(tipo, [])

        for esc in escolhidos:
            match = next((Op for Op in disponiveis if Op['nome'] == esc), None)
            if match:
                try:
                    # Converte preço do adicional para Decimal
                    preco_adicional = Decimal(str(match['price']))
                    base_price += preco_adicional
                except (ValueError, TypeError, InvalidOperation):
                    print(f"Erro ao converter preço do adicional: {esc}")
                    continue

    return base_price


def update_order_status_logic(order_id, new_status):
    ALLOWED = ["Recebido", "Em Preparo", "Saiu para Entrega", "Concluído", "Cancelado"]
    if new_status not in ALLOWED: raise ValueError("Status inválido")

    order = Order.query.get(order_id)
    if not order: raise ValueError("Pedido não encontrado")

    order.status = new_status
    db.session.commit()

    order_data = orders_schema.dump([order])[0]

    print(f"📡 Status do Pedido #{order.id} mudou para {new_status}")
    payload = {
        'order_id': order.id,
        'status': new_status,
        'user_id': order.user_id,
        'order_data': order_data
    }
    socketio.emit('status_update', convert_decimals(payload))

    return order_data


def get_order_status_logic(order_id, user_id):
    order = Order.query.get(order_id)
    if not order: raise ValueError("Pedido não encontrado")
    if str(order.user_id) != str(user_id):
        raise ValueError("Você não tem permissão para ver este pedido.")
    
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


def get_all_orders_daily():
    return get_filtered_orders({})


def convert_decimals(obj):
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj