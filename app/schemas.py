from marshmallow import fields
from .extensions import ma, db
from .models import User, Product, Order, OrderItem, Address, ChatMessage, Neighborhood, StoreSchedule
from .models import Coupon

class AddressSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = Address
        load_instance = True
        include_fk = True
# 1. Schema do Usuário
class UserSchema(ma.SQLAlchemyAutoSchema):
    addresses = ma.List(ma.Nested(AddressSchema), dump_only=True)
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

class ChatMessageSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ChatMessage
        load_instance = True
        include_fk = True

class CouponSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Coupon
        load_instance = True

class AdminUserListSchema(ma.SQLAlchemyAutoSchema):
    # [CORREÇÃO] Definimos explicitamente que este campo é um Inteiro e é apenas para leitura (dump)
    orders_count = fields.Int(dump_only=True)

    class Meta:
        model = User
        # Agora o Marshmallow sabe de onde tirar o 'orders_count' (da linha acima)
        fields = ("id", "name", "email", "whatsapp", "role", "orders_count")
        load_instance = True

class NeighborhoodSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Neighborhood
        load_instance = True

class StoreScheduleSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = StoreSchedule
        load_instance = True


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

address_schema = AddressSchema()
addresses_schema = AddressSchema(many=True)


chat_message_schema = ChatMessageSchema()
chat_messages_schema = ChatMessageSchema(many=True)

coupon_schema = CouponSchema()
coupons_schema = CouponSchema(many=True)
admin_users_schema = AdminUserListSchema(many=True)

neighborhood_schema = NeighborhoodSchema()
neighborhoods_schema = NeighborhoodSchema(many=True)


schedule_list_schema = StoreScheduleSchema(many=True)