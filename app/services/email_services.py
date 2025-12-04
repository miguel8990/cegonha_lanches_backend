# app/services/email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app
import os
import threading


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
    <p>Ou copie este link: {reset_link}</p>
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