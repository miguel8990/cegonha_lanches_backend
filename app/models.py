from datetime import datetime
from .extensions import db
import json


# ... (User continua igual ou atualizamos no Ticket #009) ...
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='client')

    @property
    def is_admin(self):
        return self.role in ['admin', 'super_admin']


    # [TICKET #009] Novos campos de perfil (Preparando para o futuro)
    whatsapp = db.Column(db.String(20))
    street = db.Column(db.String(200))

    number = db.Column(db.String(20))
    neighborhood = db.Column(db.String(100))
    complement = db.Column(db.String(100))
    orders = db.relationship('Order', backref='customer', lazy=True)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email, "role": self.role}


# ... (Product continua igual) ...
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

    # [NOVO] Snapshot do Cliente (Endereço completo na hora da compra)
    customer_name = db.Column(db.String(100))  # Importante caso o User seja deletado
    customer_phone = db.Column(db.String(20))  # WhatsApp

    street = db.Column(db.String(200))  # Antigo 'address'
    number = db.Column(db.String(20))
    neighborhood = db.Column(db.String(100))  # Bairro (Novo)
    complement = db.Column(db.String(100))  # Apto/Casa (Novo)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    items = db.relationship('OrderItem', backref='order', lazy=True)

    payment_method = db.Column(db.String(50))  # ex: 'credit_card', 'pix', 'cash_on_delivery'
    payment_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Float, nullable=False)

    # [NOVO] Guarda: "Carne: Frango, Adicional: Bacon" em formato JSON
    customizations_json = db.Column(db.Text, default='{}')