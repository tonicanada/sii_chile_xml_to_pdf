from fastapi_mail import ConnectionConfig
import os
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)



MAIL_CONF = ConnectionConfig(
    MAIL_USERNAME = os.getenv("SMTP_USER"),
    MAIL_PASSWORD = os.getenv("SMTP_PASS"),
    MAIL_FROM = os.getenv("SMTP_FROM", "noreply@example.com"),
    MAIL_PORT = int(os.getenv("SMTP_PORT", 587)),
    MAIL_SERVER = os.getenv("SMTP_HOST", "smtp.example.com"),
    MAIL_STARTTLS=True,   # 👈 usa esto para STARTTLS (587)
    MAIL_SSL_TLS=False,   # 👈 usa esto en lugar de MAIL_SSL
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)
