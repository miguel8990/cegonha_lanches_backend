from ..models import Coments, User
from ..extensions import db
import bleach

try:
    from ..utils.bad_words import BLOCKLIST
except ImportError:
    BLOCKLIST = set() # Evita erro se o arquivo não existir


def create_coment(dados, user_id):
  raw_coment = dados.get('coment', '')
  comentario_texto = dados.get("coment", "").strip()

  
  raw_coment = set(comentario_texto.lower().split())
    
  if BLOCKLIST.intersection(raw_coment):
    return {"error": "Seu comentário contém palavras impróprias. Por favor, seja respeitoso."}, 400
  coment = bleach.clean(raw_coment, tags=[], strip=True, attributes={}).strip()
  stars = dados.get('stars')
  

  if any(palavra in coment.lower() for palavra in palavras_proibidas):
     return {"error": "Por gentileza não utilize palavras ofensivas"}, 400
  if not user_id:
    return {"error": "Usuario não identificado"}, 400
  
  try:
    stars = int(dados.get('stars', 0))
  except:
    stars = 0

  if stars < 1 or stars > 5:
    return {"error": "A avaliação deve ser entre 1 e 5 estrelas."}, 401
  if not coment:
    return {"error": "O comentario não pode estar vazio."}, 400
  
  novo_comentario = Coments(
    user_id=user_id,
    coment=coment,
    stars=stars
  )

  try:
    db.session.add(novo_comentario)
    db.session.commit()
    return {"msg": "Avaliação enviada com sucesso!"}, 201
  except Exception as e:
    db.session.rollback()
    return {"error": "Erro ao salvar avaliação"}, 500
  

def get_all_coments(order='recent'):
    """
    Busca comentários com ordenação dinâmica.
    order: 'stars_asc' (1-5), 'stars_desc' (5-1), 'recent' (Padrão)
    """
    query = Coments.query

    if order == 'stars_desc':
        # Melhores avaliações primeiro (5 -> 1)
        query = query.order_by(Coments.stars.desc(), Coments.timestamp.desc())
    elif order == 'stars_asc':
        # Piores avaliações primeiro (1 -> 5)
        query = query.order_by(Coments.stars.asc(), Coments.timestamp.desc())
    else:
        # Padrão: Mais recentes primeiro
        query = query.order_by(Coments.timestamp.desc())

    raw_coments = query.all()
    return [c.to_dict() for c in raw_coments]

def search_coment(dados):
    search_query = dados.get('search', '')

    if search_query:
        # Busca filtrada: Joga nome do User e busca parcial (ilike)
        raw_coments = Coments.query.join(User).filter(
            User.name.ilike(f"%{search_query}%")
        ).all()
    else:
        # Busca normal: Se não tem busca, retorna TUDO (conforme seu comentário sugeria)
        # Se preferir dar erro, mantenha o seu return original
        return {"error": "Nenhum resultado encontrado"}, 400

    # TRANSFORMAÇÃO DE DADOS (Essencial)
    # Converte a lista de objetos do banco para lista de dicionários (JSON)
    results = [c.to_dict() for c in raw_coments]

    # Retorna 200 (Sucesso) e não 201
    return {"results": results, "count": len(results)}, 200




      
def delete_self_coment(comment_id, user_id):
    """
    Remove um comentário específico, garantindo que pertença ao usuário.
    """
    # 1. Busca precisa pelo ID do comentário
    comentario = Coments.query.filter_by(id=comment_id).first()

    # 2. Verifica se existe
    if not comentario:
        return {"error": "Comentário não encontrado."}, 404
    
    # --- DEBUG (Pode remover depois) ---
    print(f"DEBUG TYPE: DB={type(comentario.user_id)} TOKEN={type(user_id)}")

    # 3. Verifica a propriedade (Segurança) [CORREÇÃO AQUI]
    # Convertemos ambos para string para garantir que 9 seja igual a "9"
    if str(comentario.user_id) != str(user_id):
        return {"error": "Você não tem permissão para apagar este comentário."}, 403

    # 4. Operação de Deleção
    try:
        db.session.delete(comentario)
        db.session.commit()
        return {"msg": "Comentário removido com sucesso."}, 200
    except Exception as e:
        db.session.rollback()
        print(f"ERRO DELEÇÃO: {e}")
        return {"error": "Erro ao tentar deletar o comentário."}, 500
    

def delete_coment(comment_id):
    """
    Remove um comentário específico, garantindo que pertença ao usuário.
    """
    # 1. Busca precisa pelo ID do comentário usando filter_by
    comentario = Coments.query.filter_by(id=comment_id).first()

    # 2. Verifica se existe
    if not comentario:
        return {"error": "Comentário não encontrado."}, 404

    # 4. Operação de Deleção
    try:
        db.session.delete(comentario)
        db.session.commit()
        return {"msg": "Comentário removido com sucesso."}, 200
    except Exception:
        db.session.rollback()
        return {"error": "Erro ao tentar deletar o comentário."}, 500
      

def update_coment(comment_id, user_id, novos_dados):
    """
    Atualiza um comentário existente (apenas texto e estrelas).
    """
    comentario = Coments.query.filter_by(id=comment_id).first()

    if not comentario:
        return {"error": "Comentário não encontrado."}, 404

    # Validação de Dono
    if str(comentario.user_id) != str(user_id):
        return {"error": "Sem permissão para editar."}, 403

    novo_texto = novos_dados.get("coment", "").strip()
    novas_stars = novos_dados.get("stars")

    # Validações de conteúdo (igual ao create)
    if not novo_texto or not novas_stars:
        return {"error": "Texto e nota são obrigatórios."}, 400

    # Filtro de Palavrões na Edição
    palavras_no_texto = set(novo_texto.lower().split())
    if BLOCKLIST.intersection(palavras_no_texto):
        return {"error": "O texto editado contém palavras impróprias."}, 400

    try:
        # Sanitização e Update
        comentario.coment = bleach.clean(novo_texto, tags=[], strip=True)
        comentario.stars = int(novas_stars)
        
        db.session.commit()
        return {"msg": "Comentário atualizado!"}, 200
    except Exception as e:
        db.session.rollback()
        return {"error": "Erro ao atualizar."}, 500