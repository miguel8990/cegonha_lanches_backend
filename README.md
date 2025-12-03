# Cegonha Lanches - API Backend

Servidor RESTful desenvolvido em Python com Flask, responsável por toda a lógica de negócios, banco de dados e segurança do sistema de delivery.

## Tecnologias
- **Linguagem:** Python 3.11+
- **Framework:** Flask
- **Banco de Dados:** SQLite (com SQLAlchemy ORM)
- **Autenticação:** Flask-JWT-Extended
- **Migrações:** Flask-Migrate (Alembic)
- **Serialização:** Marshmallow

## Arquitetura
O projeto segue o padrão MSC (Model-Service-Controller) para organização e escalabilidade:
- **Routes (Controller):** Recebem as requisições HTTP e validam tokens.
- **Services:** Contêm a lógica de negócios (cálculos, regras, validações).
- **Models:** Definem a estrutura do banco de dados.

## Configuração e Instalação

1. Crie e ative um ambiente virtual (.venv):
   python -m venv .venv
   .venv\Scripts\activate  (Windows)

2. Instale as dependências:
   pip install -r requiriments.txt

3. Configure as variáveis de ambiente:
   Crie um arquivo .env na raiz com:
   SUPER_ADMIN_EMAIL=seu_email@email.com
   SUPER_ADMIN_PASSWORD=sua_senha
   JWT_SECRET_KEY=sua_chave_jwt

4. Inicialize o Banco de Dados:
   flask db upgrade
   python seed.py  (Cria admin e produtos iniciais)

## Como Rodar
Execute o comando na raiz do projeto:
python run.py

O servidor rodará em: http://localhost:5000
