# app/services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import os
import threading


# import requests  <-- COMENTADO: Não utilizado
# from flask import url_for <-- COMENTADO: Não utilizado


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


def send_reset_email(to_email, link_url):  # <-- MUDANÇA: Recebe link_url, não só o token
    """
    Monta o e-mail de recuperação de senha.
    """
    # --- CÓDIGO ANTIGO COMENTADO (Lógica de URL movida para o Service) ---
    # frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:8000')
    # reset_link = f"{frontend_url}/reset.html?token={reset_token}"
    # ---------------------------------------------------------------------

    # Agora usamos o link que veio pronto
    reset_link = link_url

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

    app = current_app._get_current_object()
    thread = threading.Thread(target=_send_async_email, args=(app, msg))
    thread.start()


def send_verification_email(user_email, user_name, link_url):  # <-- MUDANÇA: Recebe link_url
    """
    Envia o e-mail de verificação usando o servidor SMTP configurado (padronizado).
    """


    magic_link = link_url

    sender = os.getenv('MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME'))
    subject = "Confirme seu cadastro - Cegonha Lanches"

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

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = user_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    try:
        app = current_app._get_current_object()
        thread = threading.Thread(target=_send_async_email, args=(app, msg))
        thread.start()
        return True
    except Exception as e:
        print(f"❌ Erro ao preparar envio de email: {str(e)}")
        return False


def send_magic_link_email(to_email, user_name, link_url):
    """
    Envia o Magic Link para login sem senha.
    (Esta função já estava correta, recebendo link_url)
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