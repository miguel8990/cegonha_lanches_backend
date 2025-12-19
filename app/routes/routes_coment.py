from flask import request, jsonify, Blueprint
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.coment_service import (create_coment, get_all_coments,search_coment,
                                          delete_coment, delete_self_coment, update_coment)
from app.decorators import admin_required


bp_coment = Blueprint('avaliar', __name__)

@bp_coment.route('', methods=['POST'])
@jwt_required()
def avaliar_produto():
  dados = request.get_json()
  user_id = get_jwt_identity()
  resposta, status = create_coment(dados, user_id)
  return jsonify(resposta), status


@bp_coment.route('/listar', methods=['GET'])
def listar_comentarios():
  order = request.args.get('order', 'recent')
  resultado = get_all_coments()
  return jsonify(resultado), 200

@bp_coment.route('/pesquisar', methods=['GET'])
@admin_required()
def pesquisar_comentarios():
  dados = request.args
  resultado, status = search_coment(dados)
  return jsonify(resultado), status


@bp_coment.route('/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def deletar_minha_avaliacao(comment_id):
    current_user_id = get_jwt_identity()
    print(f"DEBUG ROTA: Usuário ID {current_user_id} tentando deletar Comentário {comment_id}") # <--- ADICIONE
    
    resposta, status = delete_self_coment(comment_id, current_user_id)
    
    return jsonify(resposta), status

@bp_coment.route('/admin/<int:comment_id>', methods=['DELETE'])
@admin_required()
def deletar_avaliacao_admin(comment_id):
    
    
    resposta, status = delete_coment(comment_id)
    
    return jsonify(resposta), status


@bp_coment.route('/<int:comment_id>', methods=['PUT'])
@jwt_required()
def editar_minha_avaliacao(comment_id):
    user_id = get_jwt_identity()
    dados = request.get_json()
    resposta, status = update_coment(comment_id, user_id, dados)
    return jsonify(resposta), status