from marshmallow import fields
from .extensions import ma, db
from .models import User, Product, Order, OrderItem


# 1. Schema do Usuário
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        sqla_session = db.session
        # SEGURANÇA: Exclui a senha e orders (para não carregar histórico inteiro sem querer)
        exclude = ('password_hash', 'orders')


# 2. Schema do Produto
class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True
        sqla_session = db.session


# 3. Schema do Item de Pedido
class OrderItemSchema(ma.SQLAlchemyAutoSchema):
    # Nested: Traz os dados do Produto dentro do Item (para exibir o nome, imagem, etc)
    product = ma.Nested(ProductSchema, dump_only=True)

    class Meta:
        model = OrderItem
        load_instance = True
        include_fk = True  # Mantém product_id e order_id visíveis
        sqla_session = db.session


# 4. Schema do Pedido
class OrderSchema(ma.SQLAlchemyAutoSchema):
    # Nested: Traz a lista completa de itens dentro do pedido
    # 'items' deve corresponder ao nome do relationship no models.py
    items = ma.List(ma.Nested(OrderItemSchema), dump_only=True)

    # Nested: Traz dados básicos do usuário (opcional, útil para o admin)
    user = ma.Nested(UserSchema, only=("id", "name", "email", "whatsapp"), dump_only=True)

    class Meta:
        model = Order
        load_instance = True
        include_fk = True
        sqla_session = db.session


# --- INSTÂNCIAS (SINGLE E LISTAS) ---

# Usuários
user_schema = UserSchema()
users_schema = UserSchema(many=True)

# Produtos
product_schema = ProductSchema()
products_schema = ProductSchema(many=True)

# Pedidos
order_schema = OrderSchema()
orders_schema = OrderSchema(many=True)

# Itens de Pedido (caso precise manipular isoladamente)
order_item_schema = OrderItemSchema()
order_items_schema = OrderItemSchema(many=True)