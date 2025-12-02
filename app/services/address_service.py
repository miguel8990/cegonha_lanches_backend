from ..models import Address, db
from ..schemas import address_schema, addresses_schema


def add_address_logic(user_id, data):
    # Se for o primeiro endereço, já marca como ativo
    has_address = Address.query.filter_by(user_id=user_id).first()
    is_first = has_address is None

    new_addr = Address(
        user_id=user_id,
        street=data['street'],
        number=data['number'],
        neighborhood=data['neighborhood'],
        complement=data.get('complement', ''),
        is_active=is_first  # True se for o primeiro
    )
    db.session.add(new_addr)
    db.session.commit()
    return address_schema.dump(new_addr)


def get_user_addresses(user_id):
    addrs = Address.query.filter_by(user_id=user_id).all()
    return addresses_schema.dump(addrs)


def set_active_address(user_id, address_id):
    # 1. Desativa todos deste usuário
    Address.query.filter_by(user_id=user_id).update({'is_active': False})

    # 2. Ativa o escolhido
    addr = Address.query.filter_by(id=address_id, user_id=user_id).first()
    if addr:
        addr.is_active = True
        db.session.commit()
        return address_schema.dump(addr)
    raise ValueError("Endereço não encontrado.")


def delete_address(user_id, address_id):
    addr = Address.query.filter_by(id=address_id, user_id=user_id).first()
    if addr:
        db.session.delete(addr)
        db.session.commit()
        return True
    raise ValueError("Endereço não encontrado.")