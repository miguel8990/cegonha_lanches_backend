import mercadopago
from flask import current_app
from ..models import Order, db
from ..schemas import order_schema
import logging
import os

# Configuração de Logs (Importante para pagamentos)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_mp_sdk():
    token = os.getenv('MP_ACCESS_TOKEN')
    if not token:
        return None
    return mercadopago.SDK(token)


def create_preference_logic(order):
    """
    Cria a preferência de pagamento no Mercado Pago e retorna o Link.
    """
    sdk = get_mp_sdk()
    if not sdk:
        raise ValueError("Token do Mercado Pago não configurado.")

    # 1. Monta os itens no formato do MP
    items_mp = []
    for item in order.items:
        items_mp.append({
            "id": str(item.product.id),
            "title": item.product.name,
            "quantity": item.quantity,
            "unit_price": float(item.price_at_time),
            "currency_id": "BRL"
        })

    # 2. Configura o Payer (Pagador)
    # O ideal é pegar nome e sobrenome, aqui vamos dividir o nome simples
    name_parts = (order.customer_name or "Cliente").split()
    first_name = name_parts[0]
    last_name = name_parts[-1] if len(name_parts) > 1 else "Cliente"

    # 3. Monta o JSON de Preferência
    base_url = os.getenv('BASE_URL', 'http://localhost:8000')

    preference_data = {
        "items": items_mp,
        "payer": {
            "name": first_name,
            "surname": last_name,
            # "email": "email@cliente.com", # Se tiver o email do user, melhor
            "phone": {
                "area_code": "34",  # Idealmente extrair do telefone
                "number": order.customer_phone
            }
        },
        "back_urls": {
            "success": f"{base_url}/sucesso.html",
            "failure": f"{base_url}/falha.html",
            "pending": f"{base_url}/pendente.html"
        },
        "auto_return": "approved",
        "external_reference": str(order.id),  # Importante para o Webhook saber qual pedido é
        "statement_descriptor": "CEGONHA LANCHES",
    }

    # 4. Cria no Mercado Pago
    try:
        preference_response = sdk.preference().create(preference_data)
        response = preference_response["response"]

        # init_point = Link para pagar (Redirecionamento)
        # sandbox_init_point = Link de teste
        return response["init_point"]
    except Exception as e:
        logger.error(f"Erro MP: {str(e)}")
        raise ValueError("Erro ao gerar link de pagamento.")


def process_payment_logic(user_id, data):
    order_id = data.get('order_id')
    method = data.get('payment_method')

    order = Order.query.get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado.")

    if str(order.user_id) != str(user_id):
        raise ValueError("Pedido não pertence a este usuário.")

    order.payment_method = method

    # --- CENÁRIO A: Pagamento na Entrega ---
    if method in ['cash', 'card_machine', 'local_pix']:
        order.payment_status = 'pending'
        db.session.commit()
        return {
            "status": "pending",
            "message": "Pagamento na entrega.",
            "redirect_url": None
        }

    # --- CENÁRIO B: Mercado Pago (Checkout Pro) ---
    elif method == 'mercadopago':
        try:
            # Gera o link de pagamento
            checkout_url = create_preference_logic(order)

            # Não salvamos 'approved' ainda, esperamos o webhook ou o retorno
            order.payment_status = 'pending_external'
            db.session.commit()

            return {
                "status": "redirect",
                "message": "Redirecionando para o Mercado Pago...",
                "redirect_url": checkout_url  # O Front vai abrir esse link
            }
        except Exception as e:
            raise ValueError(f"Falha ao comunicar com pagamento: {str(e)}")

    else:
        raise ValueError("Método inválido.")
def process_webhook_logic(webhook_data):
    """
    Esta função é chamada automaticamente pelo Mercado Pago
    quando um Pix é pago.
    """
    # 1. Extrair ID do pedido e Status do JSON do Mercado Pago
    # (A estrutura real depende da doc do MP)
    # external_ref = webhook_data.get('external_reference')
    # status = webhook_data.get('status')

    # Simulando lógica:
    # order = Order.query.get(external_ref)
    # if status == 'approved':
    #     order.payment_status = 'approved'
    #     order.status = 'Em Preparo' # Automatiza a cozinha!
    #     db.session.commit()

    return True


def admin_confirm_payment_logic(order_id):
    """
    Função para o Admin confirmar manualmente que recebeu o dinheiro/cartão.
    """
    order = Order.query.get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado.")

    order.payment_status = 'approved'
    db.session.commit()

    return order_schema.dump(order)