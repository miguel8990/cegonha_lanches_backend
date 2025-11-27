import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Segurança básica
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-super-secreta-do-desenvolvedor'

    # Banco de Dados
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///cegonha.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Configuração do JWT (Sistema de Token para Login)
    # Isso define que o token de login expira em 1 dia, por exemplo
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'chave-secreta-jwt'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)