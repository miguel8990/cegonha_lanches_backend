from ..models import ChatMessage, db, User
from ..schemas import chat_messages_schema, chat_message_schema
from datetime import datetime, timedelta
from sqlalchemy import func
from ..extensions import socketio
import bleach
try:
    from ..utils.bad_words import BLOCKLIST
except ImportError:
    BLOCKLIST = set() # Evita erro se o arquivo não existir

SPAM_COOLDOWN_SECONDS = 2  # Tempo mínimo entre mensagens
MAX_HISTORY_CHARS = 20000  # Limite de caracteres no histórico
def send_message_logic(user_id, text, is_admin=False):
    """
    Salva uma nova mensagem com validação, sanitização e resposta automática.
    """
    # 1. Validação Básica (Deve vir ANTES de qualquer processamento)
    if not text or not isinstance(text, str) or not text.strip():
        raise ValueError("Mensagem vazia.")
    
    if len(text) > 800:
        raise ValueError("Mensagem muito grande.")

    # 2. Sanitização (Remove HTML perigoso)
    # Removemos a variável inútil 'coment'
    clean_text = bleach.clean(text, tags=[], strip=True, attributes={}).strip()

    # 3. Filtro de Palavras Impróprias
    palavras_mensagem = set(clean_text.lower().split())
    if BLOCKLIST.intersection(palavras_mensagem):
        # CORREÇÃO: Lança erro em vez de retornar tupla HTTP
        raise ValueError("Seu comentário contém palavras impróprias. Por favor, seja respeitoso.")

    # 4. Verificação de Spam (Cooldown)
    # Verifica apenas se há uma mensagem anterior
    last_msg = ChatMessage.query.filter_by(user_id=user_id) \
        .order_by(ChatMessage.timestamp.desc()) \
        .first()

    if last_msg and not is_admin:
        time_diff = datetime.utcnow() - last_msg.timestamp
        if time_diff.total_seconds() < SPAM_COOLDOWN_SECONDS:
            raise ValueError("Você está enviando mensagens muito rápido. Aguarde um momento.")

    # 5. Lógica de Primeira Mensagem
    is_first_message = False
    if not is_admin:
        # Dica de Performance: Se last_msg for None, count é 0. Não precisa fazer query de count.
        if not last_msg: 
            is_first_message = True

    # 6. Persistência
    try:
        new_msg = ChatMessage(
            user_id=user_id,
            message=clean_text,
            is_from_admin=is_admin,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_msg)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"❌ Erro ao salvar mensagem: {e}")
        raise ValueError("Erro interno ao salvar mensagem.")

    # 7. Pós-processamento
    if not is_admin:
        try:
            _enforce_storage_limit(user_id)
        except Exception as e:
            print(f"⚠️ Erro ao limpar histórico antigo: {e}")

    msg_dump = chat_message_schema.dump(new_msg)
    print(f"📡 Nova mensagem chat (User {user_id})")
    socketio.emit('chat_message', msg_dump)

    # 8. Resposta Automática (Bot)
    if is_first_message:
        try:
            user = User.query.get(user_id)
            primeiro_nome = user.name.split()[0] if user and user.name else "Cliente"

            bot_text = (
                f"Olá, {primeiro_nome}! 👋 Bem-vindo ao chat do Cegonha Lanches.\n"
                "Recebemos sua mensagem e um atendente irá respondê-lo em breve. "
                "Enquanto isso, fique à vontade para consultar nosso cardápio!"
            )

            auto_reply = ChatMessage(
                user_id=user_id,
                message=bot_text,
                is_from_admin=True,
                timestamp=datetime.utcnow()
            )
            db.session.add(auto_reply)
            db.session.commit()

            bot_msg_dump = chat_message_schema.dump(auto_reply)
            socketio.emit('chat_message', bot_msg_dump)
        except Exception as e:
            print(f"❌ Erro ao enviar resposta automática: {e}")
            # Não damos raise aqui para não cancelar a mensagem do usuário que já foi salva

    return msg_dump


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