# app/services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import os
import threading
import requests
from flask import url_for


def _send_async_email(app, msg):
    """Envia o e-mail em segundo plano (background thread)"""
    with app.app_context():
        try:
            server = smtplib.SMTP(os.getenv('MAIL_SERVER'), int(os.getenv('MAIL_PORT')))
            server.starttls()  # Segurança
            server.login(os.getenv('MAIL_USERNAME'), os.getenv('MAIL_PASSWORD'))
            server.send_message(msg)
            server.quit()
            print(f"📧 E-mail enviado para: {msg['To']}")
        except Exception as e:
            print(f"❌ Erro ao enviar e-mail: {str(e)}")


def send_reset_email(to_email, reset_token):
    """
    Monta o e-mail de recuperação de senha.
    """
    # Link que o usuário vai clicar (Frontend)
    # Supondo que seu front roda na porta 8000
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8000')
    reset_link = f"{frontend_url}/reset.html?token={reset_token}"

    subject = "Cegonha Lanches - Recuperação de Senha"

    # HTML do E-mail
    html_body = f"""
    <h2>Recuperação de Senha</h2>
    <p>Olá,</p>
    <p>Recebemos uma solicitação para redefinir sua senha.</p>
    <p>Clique no botão abaixo para criar uma nova senha:</p>
    <a href="{reset_link}" style="background-color:#d93025; color:white; padding:10px 20px; text-decoration:none; border-radius:5px;">
        Redefinir Minha Senha
    </a>
    <p>Ou copie este link:</p>
    <p>{reset_link}</p>
    <p>Este link expira em 30 minutos.</p>
    <p>Se não foi você, ignore este e-mail.</p>
    """

    msg = MIMEMultipart()
    msg['From'] = os.getenv('MAIL_DEFAULT_SENDER')
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    # Pega a instância do app atual para passar para a thread
    # (Necessário porque o Flask trabalha com contextos)
    app = current_app._get_current_object()

    # Dispara a thread (não bloqueia o retorno da API)
    thread = threading.Thread(target=_send_async_email, args=(app, msg))
    thread.start()


# No arquivo app/services/email_services.py

def send_verification_email(user_email, user_name, token):
    """
    Envia o e-mail de verificação usando o servidor SMTP configurado (padronizado).
    """
    # 1. Definir a URL do Backend (API)
    # Usa API_BASE_URL se existir, senão assume localhost:5000
    base_url = os.getenv('API_BASE_URL', 'http://localhost:5000')
    magic_link = f"{base_url}/api/auth/confirm-email?token={token}"

    # 2. Configurar Remetente e Assunto
    # Tenta usar o MAIL_DEFAULT_SENDER, se não tiver, usa o MAIL_USERNAME
    sender = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))
    subject = "Confirme seu cadastro - Cegonha Lanches"

    # 3. Montar o Corpo do E-mail
    html_body = f"""
        <html>
        <body>
            <h1>Olá, {user_name}!</h1>
            <p>Falta pouco para finalizar seu cadastro.</p>
            <p>Clique no botão abaixo para confirmar seu email e liberar seus pedidos:</p>
            <a href="{magic_link}" style="background-color:#f2c94c; color:#000; padding:10px 20px; text-decoration:none; border-radius:5px; font-weight:bold;">
                CONFIRMAR EMAIL
            </a>
            <p>Ou copie o link: {magic_link}</p>
        </body>
        </html>
    """

    # 4. Criar o objeto MIME (Necessário para o smtplib)
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = user_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    # 5. Enviar usando a função assíncrona existente (_send_async_email)
    try:
        # Captura o app atual para passar para a thread (contexto do Flask)
        app = current_app._get_current_object()

        # Cria e inicia a thread usando a função que você já tem
        thread = threading.Thread(target=_send_async_email, args=(app, msg))
        thread.start()

        return True
    except Exception as e:
        print(f"❌ Erro ao preparar envio de email: {str(e)}")
        return False


# ... (mantenha os imports e as outras funções: _send_async_email, send_reset_email, etc) ...

def send_magic_link_email(to_email, user_name, link_url):
    """
    Envia o Magic Link para login sem senha.
    """
    subject = "Seu Link Mágico de Acesso ✨ - Cegonha Lanches"
    sender = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))

    html_body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; text-align: center; color: #333;">
            <div style="max-width: 500px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                <h2 style="color: #d93025;">Olá, {user_name}!</h2>
                <p>Você solicitou um acesso rápido sem senha.</p>
                <p>Clique no botão abaixo para entrar imediatamente:</p>

                <a href="{link_url}" 
                   style="display: inline-block; background-color: #f2c94c; color: #000; padding: 15px 25px; 
                          text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px; margin: 20px 0;">
                    ENTRAR AGORA
                </a>

                <p style="font-size: 12px; color: #777;">
                    Este link é válido por 15 minutos.<br>
                    Se não foi você, ignore este e-mail.
                </p>
            </div>
        </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        app = current_app._get_current_object()
        thread = threading.Thread(target=_send_async_email, args=(app, msg))
        thread.start()
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar Magic Link: {str(e)}")
        return False