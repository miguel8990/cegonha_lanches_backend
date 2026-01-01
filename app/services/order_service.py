from ..models import Order, OrderItem, Product, db, Neighborhood, Coupon, User, Address
import json
from ..schemas import orders_schema
from sqlalchemy.orm import joinedload
from datetime import datetime
from sqlalchemy import desc
from decimal import Decimal, InvalidOperation  # Importe InvalidOperation
from ..extensions import socketio


def create_order_logic(user_id, data):
    """
    Cria o pedido com:
    1. Row Locking (previne erro de estoque concorrente).
    2. Cálculo de preço via Backend (previne erro de float/fraude).
    """
    customer_data = data.get('customer', {})
    items_data = data.get('items', [])
    payment_method = data.get('payment_method')
    
    if not items_data:
        raise ValueError("O carrinho está vazio.")

    # Inicia a transação
    try:
        # 1. Cria o objeto Order (ainda sem valor total)
        new_order = Order(
            user_id=user_id,
            customer_name=customer_data.get('name'),
            customer_phone=customer_data.get('phone'),
            street=customer_data.get('address', {}).get('street'),
            number=str(customer_data.get('address', {}).get('number')),
            neighborhood=customer_data.get('address', {}).get('neighborhood'),
            complement=customer_data.get('address', {}).get('complement'),
            payment_method=payment_method,
            status='Recebido',
            total_price=0.00, # Será calculado abaixo
            delivery_fee=0.00 # Implementar lógica de taxa se houver
        )
        
        db.session.add(new_order)
        db.session.flush() # Gera o ID do pedido para usar nos itens

        calculated_total = Decimal('0.00')

        # 2. Itera sobre os itens
        for item in items_data:
            prod_id = item.get('product_id')
            qtd = item.get('quantity', 1)
            
            # 🔥 CORREÇÃO DE CONCORRÊNCIA (Ponto 3): 
            # .with_for_update() trava este produto até o fim da transação.
            # Se outro cliente tentar comprar, ele espera essa transação acabar.
            product = Product.query.filter_by(id=prod_id).with_for_update().first()
            
            if not product:
                raise ValueError(f"Produto ID {prod_id} não encontrado.")
                
            if not product.is_available or product.is_deleted:
                raise ValueError(f"O produto '{product.name}' não está mais disponível.")

            # Verifica Estoque (se aplicável)
            if product.stock_quantity is not None:
                if product.stock_quantity < qtd:
                    raise ValueError(f"Estoque insuficiente para '{product.name}'. Restam: {product.stock_quantity}")
                product.stock_quantity -= qtd

            # 🔥 CORREÇÃO DE PREÇO (Ponto 2):
            # Usamos product.price (do banco), ignoramos o preço do JSON do frontend.
            price_at_moment = product.price
            item_total = price_at_moment * qtd
            calculated_total += item_total

            # Cria o item do pedido
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=qtd,
                price_at_time=price_at_moment, # Salva o preço histórico
                customizations_json=str(item.get('customizations', {}))
            )
            db.session.add(order_item)

        # Atualiza o total do pedido com a soma confiável do backend
        new_order.total_price = calculated_total
        
        db.session.commit()
        
        return {
            "sucesso": True,
            "id": new_order.id,
            "total": str(new_order.total_price),
            "redirect_url": f"/pedido_confirmado.html?id={new_order.id}"
        }

    except Exception as e:
        db.session.rollback() # Desfaz tudo se der erro no estoque ou código
        raise e


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

    for item in order.items:
        if item.product.stock_quantity is not None:
            item.product.stock_quantity += item.quantity

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