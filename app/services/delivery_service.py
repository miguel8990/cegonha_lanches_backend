
from app.models import Neighborhood, db



def adicionar_bairro(data):
    # Verifica duplicidade

    if not data.get('name') or data.get('price') is None:
        raise ValueError('Nome e preço são obrigatorios')

    if Neighborhood.query.filter_by(name=data['name']).first():
        raise ValueError('O bairro já está cadastrado')

    price = data.get('price')
    name = data.get('name')

    if len(name) > 100:
        raise ValueError('O nome do bairro é muito grande')

    try:
        # Tenta converter. Se vier "10,50" (com vírgula), substituímos por ponto antes
        price_float = float(str(price).replace(',', '.'))
    except (ValueError, TypeError):
        raise ValueError('erro: o preço deve ser um número válido (ex: 10.50)')


    try:
        new_bairro = Neighborhood(
            name=name,
            price=price_float,
            is_active=True
        )

        db.session.add(new_bairro)
        db.session.commit()

        return (new_bairro)
    except Exception as e:
        db.session.rollback()
        raise ValueError('Erro ao salvar no banco de dados')


from app.models import Neighborhood, db


# ... (sua função adicionar_bairro já existente fica aqui acima) ...

def atualizar_bairro_logic(bairro_id, data):
    """
    Atualiza um bairro existente.
    Valida se existe e trata conversão de preço com segurança.
    """
    bairro = Neighborhood.query.get(bairro_id)

    if not bairro:
        # Usamos uma mensagem específica para a rota saber que é 404
        raise ValueError("Bairro não encontrado.")

    # 1. Atualizar Nome (com validação básica)
    if 'name' in data:
        name = data['name'].strip()
        if not name:
            raise ValueError("O nome não pode ser vazio.")
        if len(name) > 100:
            raise ValueError("Nome muito longo.")
        bairro.name = name

    # 2. Atualizar Preço (com proteção contra crash)
    if 'price' in data:
        try:
            raw_price = data['price']
            # Troca vírgula por ponto para aceitar padrão BR
            price_float = float(str(raw_price).replace(',', '.'))
            if price_float < 0:
                raise ValueError("O preço não pode ser negativo.")
            if price_float > 1000:
                raise ValueError("O valor do frete parece muito alto (máx: 1000). Verifique.")
            bairro.price = price_float
        except (ValueError, TypeError):
            raise ValueError("O preço deve ser um número válido (ex: 10.50).")

    # 3. Atualizar Status
    if 'is_active' in data:
        # Garante que seja booleano
        bairro.is_active = bool(data['is_active'])

    try:
        db.session.commit()
        return bairro
    except Exception as e:
        db.session.rollback()
        raise ValueError("Erro interno ao atualizar no banco de dados.")


def deletar_bairro_logic(bairro_id):
    """
    Remove um bairro do banco de dados.
    """
    bairro = Neighborhood.query.get(bairro_id)

    if not bairro:
        raise ValueError("Bairro não encontrado.")

    try:
        db.session.delete(bairro)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        raise ValueError("Erro ao tentar excluir o bairro.")