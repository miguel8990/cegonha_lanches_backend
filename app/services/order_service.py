from ..models import Order, OrderItem, Product, db
import json


def create_order_logic(data, user_id=None):
    # 1. Extração dos Dados do Cliente (Vem dentro de 'customer')
    customer_data = data.get('customer', {})
    address_data = customer_data.get('address', {})

    # Validação Básica
    if not address_data.get('street') or not address_data.get('number'):
        raise ValueError("Endereço e número são obrigatórios.")

    # 2. Criação do Pedido (Cabeçalho)
    new_order = Order(
        user_id=user_id,
        status='Recebido',
        total_price=0.0,  # Vamos calcular abaixo

        # Snapshot dos dados
        customer_name=customer_data.get('name'),
        customer_phone=customer_data.get('phone'),
        street=address_data.get('street'),
        number=address_data.get('number'),
        neighborhood=address_data.get('neighborhood'),
        complement=address_data.get('complement')
    )

    db.session.add(new_order)
    db.session.commit()  # Gera o ID do pedido

    # 3. Processamento dos Itens (Coração do Cálculo)
    items_list = data.get('items', [])
    total_order_value = 0.0

    for item in items_list:
        product = Product.query.get(item['product_id'])
        if not product:
            continue  # Se produto não existe, ignora (ou poderia dar erro)

        # Preço Base
        item_price = product.price

        # Pega as personalizações enviadas (Carne, Adicionais...)
        customizations = item.get('customizations', {})

        # --- LÓGICA DE CÁLCULO DE ADICIONAIS ---
        # Carregamos os detalhes do produto (onde estão os preços dos extras)
        product_details = product.get_details()

        # Exemplo: Somar Adicionais
        # O front manda: "adicionais": ["Bacon", "Ovo"]
        chosen_adicionais = customizations.get('adicionais', [])
        available_adicionais = product_details.get('adicionais', [])

        for chosen in chosen_adicionais:
            # Procura o preço desse adicional na lista do produto
            # (Segurança: usa o preço do banco, não do front)
            match = next((ad for ad in available_adicionais if ad['nome'] == chosen), None)
            if match:
                item_price += match['price']

        # Exemplo: Somar Acompanhamentos
        chosen_acompanhamentos = customizations.get('acompanhamentos', [])
        available_acompanhamentos = product_details.get('acompanhamentos', [])

        for chosen in chosen_acompanhamentos:
            match = next((ac for ac in available_acompanhamentos if ac['nome'] == chosen), None)
            if match:
                item_price += match['price']

        # 4. Salva o Item
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=item['quantity'],
            price_at_time=item_price,  # Preço unitário final calculado
            customizations_json=json.dumps(customizations)  # Salva o JSON exato
        )
        db.session.add(order_item)

        # Soma ao total do pedido
        total_order_value += (item_price * item['quantity'])

    # Atualiza o preço total do pedido no banco
    new_order.total_price = total_order_value
    db.session.commit()

    return new_order