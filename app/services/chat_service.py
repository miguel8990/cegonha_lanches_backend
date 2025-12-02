from ..models import ChatMessage, db, User
from ..schemas import chat_messages_schema, chat_message_schema
from datetime import datetime, timedelta
from sqlalchemy import func

SPAM_COOLDOWN_SECONDS = 2  # Tempo mínimo entre mensagens
MAX_HISTORY_CHARS = 20000  # Limite de caracteres no histórico
def send_message_logic(user_id, text, is_admin=False):
    """
    Salva uma nova mensagem.
    """
    last_msg = ChatMessage.query.filter_by(user_id=user_id) \
        .order_by(ChatMessage.timestamp.desc()) \
        .first()

    if last_msg:
        # Se não é admin e mandou mensagem muito rápido
        if not is_admin:
            time_diff = datetime.utcnow() - last_msg.timestamp
            if time_diff.total_seconds() < SPAM_COOLDOWN_SECONDS:
                raise ValueError("Você está enviando mensagens muito rápido. Aguarde um momento.")

    if not text or not text.strip():
        raise ValueError("Mensagem vazia.")
    if len(text) > 800:
        raise ValueError("Mensagem muito grande")
    new_msg = ChatMessage(
        user_id=user_id,
        message=text,
        is_from_admin=is_admin
    )
    db.session.add(new_msg)
    db.session.commit()
    if not is_admin:
        _enforce_storage_limit(user_id)

    return chat_message_schema.dump(new_msg)


def get_user_messages_logic(user_id):
    """
    Busca todo o histórico de conversa de um usuário.
    Ordenado por data (mais antigo primeiro).
    """
    messages = ChatMessage.query.filter_by(user_id=user_id) \
        .order_by(ChatMessage.timestamp.asc()) \
        .all()

    return chat_messages_schema.dump(messages)


def _enforce_storage_limit(user_id):
    """
    Função interna: Verifica o tamanho total das mensagens do usuário.
    Se passar de MAX_HISTORY_CHARS, deleta as mais antigas.
    """
    # Busca todas as mensagens do usuário (ordenadas da mais antiga para a nova)
    messages = ChatMessage.query.filter_by(user_id=user_id) \
        .order_by(ChatMessage.timestamp.asc()) \
        .all()

    total_chars = sum(len(m.message) for m in messages)

    if total_chars > MAX_HISTORY_CHARS:
        print(f"🧹 Limpando histórico do usuário {user_id} (Total: {total_chars} chars)...")

        # Deleta mensagens antigas até baixar do limite
        chars_removed = 0
        for msg in messages:
            if total_chars - chars_removed <= MAX_HISTORY_CHARS:
                break  # Já limpou o suficiente

            chars_removed += len(msg.message)
            db.session.delete(msg)

        db.session.commit()


def get_conversations_summary_logic():
    """
    Retorna lista de usuários que já mandaram mensagem,
    ordenada por quem mandou mensagem mais recente.
    """
    # Subquery para pegar a data da última mensagem de cada usuário
    last_msg_sub = db.session.query(
        ChatMessage.user_id,
        func.max(ChatMessage.timestamp).label('last_time')
    ).group_by(ChatMessage.user_id).subquery()

    # Join com a tabela de usuários para pegar o nome
    results = db.session.query(User, last_msg_sub.c.last_time) \
        .join(last_msg_sub, User.id == last_msg_sub.c.user_id) \
        .order_by(last_msg_sub.c.last_time.desc()) \
        .all()

    conversations = []
    for user, last_time in results:
        conversations.append({
            "user_id": user.id,
            "user_name": user.name,
            "last_interaction": last_time.isoformat()
        })

    return conversations


def get_admin_chat_history_logic(target_user_id):
    """
    Pega o histórico completo entre o restaurante e um usuário específico.
    """
    messages = ChatMessage.query.filter_by(user_id=target_user_id) \
        .order_by(ChatMessage.timestamp.asc()) \
        .all()

    return chat_messages_schema.dump(messages)