from flask import jsonify


def configure_errors(app):
    # Erro 404 (Não encontrado) customizado
    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({"error": "Recurso não encontrado", "code": 404}), 404

    # Erro 500 (Erro nosso/servidor)
    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({"error": "Erro interno do servidor. Tente mais tarde.", "code": 500}), 500

    # Exemplo: Capturando erros de validação genéricos
    @app.errorhandler(ValueError)
    def handle_value_error(e):
        return jsonify({"error": str(e), "code": 400}), 400