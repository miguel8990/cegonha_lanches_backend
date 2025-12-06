import mercadopago
from flask import current_app
from ..models import Order, db
from ..schemas import order_schema
import logging
import os

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_mp_sdk():
    """
    Recupera o SDK configurado com o Token do ambiente.
    """
    token = os.getenv('MP_ACCESS_TOKEN')
    # Validação simples para garantir que o token parece real
    if not token or len(token) < 10 or token == "SEU_ACCESS_TOKEN_AQUI":
        return None
    return mercadopago.SDK(token)

def create_preference_logic(order):
    """
    Cria a preferência de pagamento no Mercado Pago e retorna o Link (init_point).
    """
    sdk = get_mp_sdk()
    base_url = os.getenv('BASE_URL', 'http://localhost:8000')

    # --- MODO SIMULAÇÃO (Se não tiver chave válida no .env) ---
    if not sdk:
        print(f"⚠️ MODO TESTE: Chave MP não detectada ou inválida. Simulando sucesso.")
        return f"{base_url}/sucesso.html"

    # --- MODO REAL (Com Chave) ---
    try:
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
        # Separamos o nome para evitar erros, e por segurança COMENTAMOS O TELEFONE
        # O MP é muito estrito com formato de telefone, o que costuma causar erro 400.
        name_parts = (order.customer_name or "Cliente").split()
        first_name = name_parts[0]
        last_name = name_parts[-1] if len(name_parts) > 1 else "Cliente"

        preference_data = {
            "items": items_mp,
            "payer": {
                "name": first_name,
                "surname": last_name,
                "email": "teste@user.com", # Email obrigatório (pode ser o do user se tiver)
                # "phone": {
                #    "area_code": "34",
                #    "number": 999999999
                # }
                # ^ MANTENHA O TELEFONE COMENTADO para evitar erro 400 "invalid_parameter"
            },
            "back_urls": {
                "success": f"{base_url}/sucesso.html",
                "failure": f"{base_url}/falha.html",
                "pending": f"{base_url}/pendente.html"
            },
            "auto_return": "approved",
            "external_reference": str(order.id), # Importante para o Webhook identificar o pedido
            "statement_descriptor": "CEGONHA LANCHES",
        }

        # 3. Cria a preferência na API do Mercado Pago
        preference_response = sdk.preference().create(preference_data)
        response = preference_response["response"]

        # Verifica se deu certo
        if "init_point" not in response:
            logger.error(f"Erro MP Resposta: {response}")
            raise ValueError("Mercado Pago não retornou o link de pagamento.")

        # Retorna o link real para o cliente pagar
        return response["init_point"]

    except Exception as e:
        logger.error(f"Erro MP Exception: {str(e)}")
        raise ValueError("Erro ao comunicar com Mercado Pago. Verifique suas credenciais no .env")


def process_payment_logic(user_id, data):
    """
    Processa a intenção de pagamento vinda do Frontend.
    """
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
            # Gera o link de pagamento (Real ou Simulado)
            checkout_url = create_preference_logic(order)

            # Marca como pendente externo (aguardando webhook ou retorno)
            order.payment_status = 'pending_external'
            db.session.commit()

            return {
                "status": "redirect",
                "message": "Redirecionando para o Mercado Pago...",
                "redirect_url": checkout_url
            }
        except Exception as e:
            raise ValueError(f"Falha ao gerar pagamento: {str(e)}")

    else:
        raise ValueError("Método de pagamento inválido.")


def process_webhook_logic(webhook_data):
    """
    Processa a notificação (Webhook) do Mercado Pago.
    """
    sdk = get_mp_sdk()
    if not sdk:
        print("⚠️ SDK MP não configurado. Ignorando Webhook.")
        return False

    # O MP envia 'type' ou 'topic', e os dados dentro de 'data' ou 'resource'
    topic = webhook_data.get('topic') or webhook_data.get('type')
    resource_id = (webhook_data.get('data') or {}).get('id')

    # Só nos interessa quando o tópico é 'payment'
    if topic == 'payment' and resource_id:
        try:
            # Consulta o status atual do pagamento na API do MP
            payment_info = sdk.payment().get(resource_id)
            payment = payment_info.get("response", {})

            status = payment.get("status")
            order_id = payment.get("external_reference") # ID do nosso pedido

            print(f"🔔 Webhook MP: Pagamento {resource_id} p/ Pedido #{order_id} -> Status: {status}")

            if status == 'approved' and order_id:
                order = Order.query.get(int(order_id))

                if order:
                    if order.payment_status != 'approved':
                        order.payment_status = 'approved'
                        # Se quiser mudar o status da cozinha automaticamente:
                        # order.status = 'Em Preparo'
                        db.session.commit()
                        print(f"✅ Pedido #{order.id} atualizado para PAGO!")
                    else:
                        print(f"ℹ️ Pedido #{order.id} já estava pago.")
                else:
                    print(f"⚠️ Pedido #{order_id} não encontrado no banco.")

            return True

        except Exception as e:
            print(f"❌ Erro ao processar webhook MP: {str(e)}")
            return False

    return True


def admin_confirm_payment_logic(order_id):
    """
    Função para o Admin confirmar manualmente.
    """
    order = Order.query.get(order_id)
    if not order:
        raise ValueError("Pedido não encontrado.")

    order.payment_status = 'approved'
    db.session.commit()

    return order_schema.dump(order)