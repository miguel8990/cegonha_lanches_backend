from datetime import datetime
from .extensions import db
import json
import bleach
from sqlalchemy import event
from werkzeug.security import generate_password_hash, check_password_hash



class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), default='client')
    is_verified = db.Column(db.Boolean, default=False)


    # Apenas dados de contato diretos
    whatsapp = db.Column(db.String(20))

    # Relacionamentos
    orders = db.relationship('Order', backref='customer', lazy=True)
    # O cascade='all, delete-orphan' garante que se apagar o user, apaga os endereços dele
    addresses = db.relationship('Address', backref='user', lazy=True, cascade="all, delete-orphan")

    @property
    def is_admin(self):
        return self.role in ['admin', 'super_admin']

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role, "is_verified": self.is_verified}

    @property
    def password(self):
        raise AttributeError('A senha não é um atributo legível')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        if not self.password_hash:
            return False  # Usuário sem senha (conta apenas social/magic link)
        return check_password_hash(self.password_hash, password)

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    street = db.Column(db.String(200), nullable=False)
    number = db.Column(db.String(20), nullable=False)
    neighborhood = db.Column(db.String(100), nullable=False)
    complement = db.Column(db.String(100))

    is_active = db.Column(db.Boolean, default=False)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(200))
    category = db.Column(db.String(50), default='Lanche')
    details_json = db.Column(db.Text, default='{}')
    is_available = db.Column(db.Boolean, default=True)
    stock_quantity = db.Column(db.Integer, nullable=True)

    def get_details(self):
        try:
            return json.loads(self.details_json)
        except:
            return {}


class Order(db.Model):
    __tablename__ = 'order'

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Recebido')
    total_price = db.Column(db.Float, default=0.0)

    # SNAPSHOT DO CLIENTE (Dados fixos da hora da compra)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    delivery_fee = db.Column(db.Float, default=0.0)

    # O Pedido PRECISA ter endereço próprio (Snapshot)
    # Se você tirar isso, e o cliente mudar o endereço na tabela Address,
    # você vai entregar o pedido antigo no lugar errado.
    street = db.Column(db.String(200))  # <--- DESCOMENTADO
    number = db.Column(db.String(20))
    neighborhood = db.Column(db.String(100))
    complement = db.Column(db.String(100))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    items = db.relationship('OrderItem', backref='order', lazy=True)

    payment_method = db.Column(db.String(50))
    payment_status = db.Column(db.String(20), default='pending')


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Float, nullable=False)
    customizations_json = db.Column(db.Text, default='{}')
    product = db.relationship('Product')


# app/models.py
# ... imports ...

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Se True, foi o restaurante que enviou. Se False, foi o cliente.
    is_from_admin = db.Column(db.Boolean, default=False)

    # Relacionamento (Opcional, ajuda na consulta)
    # user = db.relationship('User', backref='messages')

class Neighborhood(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)

class StoreSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, unique=True, nullable=False) # 0=Dom, 1=Seg, ..., 6=Sab
    open_time = db.Column(db.String(5), default="18:30") # Formato "HH:MM"
    close_time = db.Column(db.String(5), default="22:30")
    is_closed = db.Column(db.Boolean, default=False)

# ... (resto dos models) ...

# app/models.py
# ... imports ...

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    discount_percent = db.Column(db.Integer, default=0)  # Ex: 10 para 10%
    discount_fixed = db.Column(db.Float, default=0.0)  # Ex: 5.00 para R$ 5,00

    min_purchase = db.Column(db.Float, default=0.0)  # Valor mínimo do pedido

    usage_limit = db.Column(db.Integer, nullable=True)  # Quantas pessoas podem usar (Null = infinito)
    used_count = db.Column(db.Integer, default=0)

    is_active = db.Column(db.Boolean, default=True)


# ==============================================================================
# 🛡️ SEGURANÇA: SANITIZAÇÃO AUTOMÁTICA (XSS PROTECTION)
# ==============================================================================

def sanitize_text(target, value, oldvalue, initiator):
    """
    Remove qualquer tag HTML de campos de texto antes de salvar no banco.
    Ex: "<script>alert(1)</script>" vira "alert(1)" ou "&lt;script&gt;..."
    """
    if value is not None and isinstance(value, str):
        # tags=[] significa que NENHUMA tag HTML é permitida (remove negrito, links, etc)
        # strip=True remove o conteúdo da tag perigosa se necessário
        return bleach.clean(value, tags=[], strip=True)
    return value

# Aplica a proteção nos campos onde o usuário pode escrever livremente

# 1. Produtos (Protege contra Admin mal intencionado ou invadido)
event.listen(Product.name, 'set', sanitize_text, retval=True)
event.listen(Product.description, 'set', sanitize_text, retval=True)
event.listen(Product.category, 'set', sanitize_text, retval=True)

# 2. Usuários (Protege contra nomes falsos com scripts)
event.listen(User.name, 'set', sanitize_text, retval=True)
# O email já é validado por formato, mas mal não faz
event.listen(User.email, 'set', sanitize_text, retval=True)

# 3. Chat (Muito importante! É onde usuários escrevem livremente)
event.listen(ChatMessage.message, 'set', sanitize_text, retval=True)

# 4. Pedidos (Observações e endereços podem ser vetores de ataque)
event.listen(Order.customer_name, 'set', sanitize_text, retval=True)
event.listen(Order.street, 'set', sanitize_text, retval=True)
event.listen(Order.complement, 'set', sanitize_text, retval=True)
event.listen(Order.neighborhood, 'set', sanitize_text, retval=True)

# 5. Endereços
event.listen(Address.street, 'set', sanitize_text, retval=True)
event.listen(Address.complement, 'set', sanitize_text, retval=True)
event.listen(Address.neighborhood, 'set', sanitize_text, retval=True)