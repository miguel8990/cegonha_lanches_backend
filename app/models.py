from datetime import datetime
from .extensions import db
import json


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='client')

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
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}


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

# ... (resto dos models) ...