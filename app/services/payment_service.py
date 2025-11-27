from ..models import Order, db


def process_webhook(data):
    # Lógica simplificada: Vamos supor que o Mercado Pago mande o ID do nosso pedido
    # num campo chamado 'external_reference' e o status em 'status'.

    # Nota: A estrutura real do JSON do Mercado Pago é complexa,
    # mas para aprender, vamos focar na lógica interna.

    order_id = data.get('external_reference')
    payment_status = data.get('status')  # approved, pending, rejected

    if not order_id:
        return {"error": "Pedido não identificado"}, 400

    order = Order.query.get(order_id)

    if not order:
        return {"error": "Pedido não encontrado no banco"}, 404

    # Atualiza o status do pedido baseado no pagamento
    if payment_status == 'approved':
        order.status = 'Preparando'  # Pagou, a cozinha começa a fazer!
        print(f"Pedido {order_id} pago! Enviando para cozinha...")
    elif payment_status == 'rejected':
        order.status = 'Cancelado'

    db.session.commit()

    return {"status": "updated"}, 200