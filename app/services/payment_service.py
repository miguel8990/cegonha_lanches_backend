from ..models import Order, db
from ..schemas import order_schema
import logging

# Configuração de Logs (Importante para pagamentos)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- CONFIGURAÇÃO MERCADO PAGO (FUTURO) ---
# import mercadopago
# sdk = mercadopago.SDK("SEU_ACCESS_TOKEN_AQUI")

def process_payment_logic(user_id, data):
    """
    Recebe a intenção de pagamento do cliente.
    data = { "order_id": 12, "payment_method": "pix_online" }
    """
    order_id = data.get('order_id')
    method = data.get('payment_method')  # 'cash', 'card_machine', 'pix_online'

    order = Order.query.get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado.")

    # Segurança: Verifica se o pedido é do usuário logado
    if str(order.user_id) != str(user_id):
        raise ValueError("Pedido não pertence a este usuário.")

    # Salva a escolha do método
    order.payment_method = method

    # --- LÓGICA DE DECISÃO ---

    # CENÁRIO A: Pagamento na Entrega (Maquininha ou Dinheiro)
    if method in ['cash', 'card_machine', 'local_pix']:
        # Não processamos nada online. Apenas registramos.
        order.payment_status = 'pending'  # Fica pendente até o motoboy voltar
        db.session.commit()

        return {
            "status": "pending",
            "message": "Pagamento será realizado na entrega.",
            "action_required": None
        }

    # CENÁRIO B: Pagamento Online (Mercado Pago / Pix Automático)
    elif method == 'pix_online':
        # --- CÓDIGO MERCADO PAGO (COMENTADO PARA FUTURO) ---
        """
        payment_data = {
            "transaction_amount": order.total_price,
            "description": f"Pedido #{order.id} - Cegonha",
            "payment_method_id": "pix",
            "payer": {
                "email": "email_do_cliente@test.com",
                "first_name": order.customer_name
            }
        }
        # mp_response = sdk.payment().create(payment_data)
        # qr_code = mp_response["response"]["point_of_interaction"]["transaction_data"]["qr_code"]
        # order.payment_status = 'pending'
        # db.session.commit()

        # return {
        #    "status": "pending",
        #    "action_required": "scan_qr",
        #    "qr_code": qr_code
        # }
        """
        # Por enquanto, retornamos erro se tentar usar sem configurar
        raise ValueError("Pagamento online indisponível no momento. Escolha pagamento na entrega.")

    else:
        raise ValueError("Método de pagamento inválido.")


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