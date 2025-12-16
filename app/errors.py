from flask import jsonify
# Importação necessária para tipagem correta do erro, se desejar
from flask_limiter.errors import RateLimitExceeded 

def configure_errors(app):
    # Erro 404 (Não encontrado)
    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({"error": "Recurso não encontrado", "code": 404}), 404

    # Erro 500 (Erro do servidor)
    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"error": "Erro interno do servidor. Tente mais tarde.", "code": 500}), 500

    # Erros de validação
    @app.errorhandler(ValueError)
    def handle_value_error(e):
        return jsonify({"error": str(e), "code": 400}), 400

    # =========================================================================
    # 🔥 CORREÇÃO: Tratamento do Erro 429 (Rate Limit) para JSON
    # =========================================================================
    @app.errorhandler(429)
    def ratelimit_handler(e):
        # e.description contém a mensagem que você define no @limiter.limit
        return jsonify({
            "error": "Muitas requisições",
            "message": str(e.description), # Ex: "8 per hour" ou sua msg personalizada
            "code": 429
        }), 429