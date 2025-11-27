from .extensions import ma, db
from .models import Product, Order




# Schema do Produto
class ProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Product
        load_instance = True # Permite carregar dados direto para o Model
        sqla_session = db.session

# Schema do Pedido
class OrderSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Order
        include_fk = True # Inclui os IDs estrangeiros (user_id)
        load_instance = True

# Instâncias para usar nas rotas/services
product_schema = ProductSchema()
products_schema = ProductSchema(many=True) # Para listas de produtos