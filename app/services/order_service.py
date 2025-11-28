from ..models import Order, OrderItem, Product, db
import json
from ..schemas import orders_schema
from sqlalchemy.orm import joinedload  # Import necessário para a otimização (Ticket #ORD-004)
from datetime import datetime, time


def create_order_logic(data, user_id=None):
    # 1. Validação e Cabeçalho
    customer_data = data.get('customer', {})
    address_data = customer_data.get('address', {})

    if not address_data.get('street') or not address_data.get('number'):
        raise ValueError("Endereço e número são obrigatórios.")

    new_order = Order(
        user_id=user_id,
        status='Recebido',
        total_price=0.0,
        customer_name=customer_data.get('name'),
        customer_phone=customer_data.get('phone'),
        street=address_data.get('street'),
        number=address_data.get('number'),
        neighborhood=address_data.get('neighborhood'),
        complement=address_data.get('complement')
    )

    db.session.add(new_order)
    db.session.flush()  # Garante o ID do pedido (Ticket #ORD-001)

    # 2. Processamento dos Itens
    items_list = data.get('items', [])
    total_order_value = 0.0

    if not items_list:
        raise ValueError("O pedido deve conter pelo menos um item.")

    for item_data in items_list:
        product = Product.query.get(item_data['product_id'])

        # Validação de produto (Ticket #ORD-002)
        if not product:
            raise ValueError(f"Produto com ID {item_data['product_id']} não encontrado.")

        customizations = item_data.get('customizations', {})

        # [REFATORAÇÃO #ORD-003] A lógica de cálculo agora é uma chamada simples!
        final_price = _calculate_item_price(product, customizations)

        # Criação do Item no Banco
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=item_data['quantity'],
            price_at_time=final_price,
            customizations_json=json.dumps(customizations)
        )
        db.session.add(order_item)

        total_order_value += (final_price * item_data['quantity'])

    # 3. Finalização
    new_order.total_price = total_order_value
    db.session.commit()

    return new_order


def get_order_logic(user_id):
    # [CORREÇÃO #ORD-004] Eager Loading para evitar o erro de atributo 'items'
    orders = Order.query.options(joinedload(Order.items)) \
        .filter_by(user_id=user_id) \
        .order_by(Order.date_created.desc()) \
        .all()
    return orders_schema.dump(orders)


# --- FUNÇÕES AUXILIARES (PRIVADAS) ---

def _calculate_item_price(product, customizations):
    """
    Calcula o preço unitário final de um produto somando seus adicionais.
    """
    base_price = product.price
    product_details = product.get_details()

    # Soma Adicionais
    chosen_adicionais = customizations.get('adicionais', [])
    available_adicionais = product_details.get('adicionais', [])

    for chosen in chosen_adicionais:
        match = next((ad for ad in available_adicionais if ad['nome'] == chosen), None)
        if match:
            base_price += match['price']

    # Soma Acompanhamentos
    chosen_acompanhamentos = customizations.get('acompanhamentos', [])
    available_acompanhamentos = product_details.get('acompanhamentos', [])

    for chosen in chosen_acompanhamentos:
        match = next((ac for ac in available_acompanhamentos if ac['nome'] == chosen), None)
        if match:
            base_price += match['price']

    return base_price

def get_all_orders_daily():
    today = datetime.utcnow().date()
    start_of_day = datetime.combine(today, time.min)
    end_of_day = datetime.combine(today, time.max)
    orders = Order.query.options(joinedload(Order.items)) \
                    .filter(Order.date_created >= start_of_day, Order.date_created <= end_of_day) \
                    .order_by(Order.date_created.desc()) \
                    .all()


    return orders_schema.dump(orders)


def update_order_status_logic(order_id, new_status):
    """
    Função para a Cozinha/Admin avançar o pedido.
    """
    # Lista de status permitidos para evitar erros de digitação
    ALLOWED_STATUS = ["Recebido", "Em Preparo", "Saiu para Entrega", "Concluído", "Cancelado"]

    if new_status not in ALLOWED_STATUS:
        raise ValueError(f"Status inválido. Use: {ALLOWED_STATUS}")

    order = Order.query.get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado.")

    order.status = new_status
    db.session.commit()

    # Retorna o pedido atualizado
    return orders_schema.dump([order])[0]  # Reusa o schema existente


def get_order_status_logic(order_id):
    """
    Função leve para o Cliente consultar 'automaticamente' (Polling).
    """
    order = Order.query.get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado.")

    return {"id": order.id, "status": order.status}


# app/services/order_service.py

# ... (outras funções acima) ...

def cancel_order_by_client_logic(order_id, user_id):
    """
    Permite que o cliente cancele o PRÓPRIO pedido,
    mas apenas se ainda estiver com status 'Recebido'.
    """
    order = Order.query.get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado.")

    # 1. Segurança: Verifica se o pedido é mesmo do usuário logado
    # Convertemos user_id para int/str para garantir a comparação correta
    if str(order.user_id) != str(user_id):
        raise ValueError("Você não tem permissão para cancelar este pedido.")

    # 2. Regra de Negócio: Não pode cancelar se a cozinha já começou
    if order.status != 'Recebido':
        raise ValueError("O pedido já está em preparo e não pode ser cancelado pelo app. Ligue para o restaurante.")

    order.status = 'Cancelado'
    db.session.commit()

    return order




# app/services/order_service.py

# ... (outras funções) ...

def soft_delete_order_by_admin_logic(order_id):
    """
    Soft Delete (Exclusão Suave):
    O Admin marca o pedido como 'Cancelado', mas ele continua no banco
    para fins de histórico e contabilidade.
    """
    order = Order.query.get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado.")

    # Em vez de apagar (db.session.delete), apenas mudamos o status.
    # Isso funciona como um "Cancelar Forçado" que o Admin pode fazer a qualquer momento.
    order.status = 'Cancelado'

    db.session.commit()

    return order
