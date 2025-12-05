from ..models import Order, OrderItem, Product, db
import json
from ..schemas import orders_schema
from sqlalchemy.orm import joinedload  # Import necessário para a otimização (Ticket #ORD-004)
from datetime import datetime, time
from ..models import Coupon



def create_order_logic(data, user_id=None):
    # 1. Validação e Cabeçalho
    customer_data = data.get('customer', {})
    address_data = customer_data.get('address', {})
    payment_method_chosen = data.get('payment_method', 'Não informado')
    coupon_code = data.get('coupon_code')  # <--- Captura o código enviado

    if not address_data.get('street') or not address_data.get('number'):
        raise ValueError("Endereço e número são obrigatórios.")

    new_order = Order(
        user_id=user_id,
        status='Recebido',
        total_price=0.0,
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

    # 2. Processamento dos Itens (Cálculo do Total Bruto)
    items_list = data.get('items', [])
    total_order_value = 0.0

    if not items_list:
        raise ValueError("O pedido deve conter pelo menos um item.")

    for item_data in items_list:
        # ... (Lógica existente de processamento dos itens) ...
        # Mantenha o loop for igual ao que você já tem
        product = Product.query.get(item_data['product_id'])
        if not product:
            raise ValueError(f"Produto ID {item_data['product_id']} não encontrado.")

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

    # 3. Aplicação do Cupom (Segurança Backend)
    if coupon_code:
        coupon = Coupon.query.filter_by(code=coupon_code, is_active=True).first()

        if not coupon:
            raise ValueError(f"Cupom '{coupon_code}' inválido ou expirado.")

        # Verifica limite de uso global
        if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
            raise ValueError("Este cupom atingiu o limite de usos.")

        # Verifica valor mínimo
        if total_order_value < coupon.min_purchase:
            raise ValueError(f"O valor mínimo para este cupom é R$ {coupon.min_purchase:.2f}")

        # Calcula desconto
        discount = 0.0
        if coupon.discount_percent:
            discount = total_order_value * (coupon.discount_percent / 100)
        elif coupon.discount_fixed:
            discount = coupon.discount_fixed

        # Aplica desconto (não deixa ficar negativo)
        total_order_value = max(0.0, total_order_value - discount)

        # Incrementa contador de uso
        coupon.used_count += 1

    # 4. Finalização
    new_order.total_price = total_order_value
    db.session.commit()

    payment_response = None
    if payment_method_chosen == 'mercadopago':
        from app.services import payment_service
        # Prepara dados para o payment service
        pay_data = {"order_id": new_order.id, "payment_method": "mercadopago"}
        payment_response = payment_service.process_payment_logic(user_id, pay_data)

    # Retornamos um dicionário combinado
    result = orders_schema.dump([new_order])[0]

    if payment_response and payment_response.get('redirect_url'):
        result['redirect_url'] = payment_response['redirect_url']

    return result




def get_order_logic(user_id):
    # [CORREÇÃO #ORD-004] Eager Loading para evitar o erro de atributo 'items'
    orders = Order.query.options(joinedload(Order.items)) \
        .filter_by(user_id=user_id) \
        .order_by(Order.date_created.desc()) \
        .all()
    return orders_schema.dump(orders)


# --- FUNÇÕES AUXILIARES (PRIVADAS) ---

def _calculate_item_price(product, customizations):
    base_price = product.price
    product_details = product.get_details()

    # Soma Adicionais
    chosen_adicionais = customizations.get('adicionais', [])
    available_adicionais = product_details.get('adicionais', [])
    for chosen in chosen_adicionais:
        match = next((ad for ad in available_adicionais if ad['nome'] == chosen), None)
        if match: base_price += match['price']

    # Soma Acompanhamentos
    chosen_acompanhamentos = customizations.get('acompanhamentos', [])
    available_acompanhamentos = product_details.get('acompanhamentos', [])
    for chosen in chosen_acompanhamentos:
        match = next((ac for ac in available_acompanhamentos if ac['nome'] == chosen), None)
        if match: base_price += match['price']

    # [NOVO] Soma Bebidas
    chosen_bebidas = customizations.get('bebidas', [])
    available_bebidas = product_details.get('bebidas', [])
    for chosen in chosen_bebidas:
        match = next((beb for beb in available_bebidas if beb['nome'] == chosen), None)
        if match: base_price += match['price']

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
