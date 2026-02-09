# -*- coding: utf-8 -*-
"""
답장 메일 발송. op@allwayzio.com (Daum SMTP) 계정으로 발송.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.utils import formataddr
import logging

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS

logger = logging.getLogger(__name__)


def send_mail(to: str, subject: str, body: str) -> bool:
    """
    SMTP로 메일 발송. 발신자는 config의 SMTP_USER(op@allwayzio.com).
    포트 465면 SSL, 587이면 STARTTLS 사용.
    """
    if not SMTP_PASS:
        logger.warning("SMTP_PASS not set, cannot send mail")
        return False
    to = (to or "").strip()
    if not to:
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = formataddr((SMTP_USER, SMTP_USER))
        msg["To"] = to
        if SMTP_PORT == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx) as conn:
                conn.login(SMTP_USER, SMTP_PASS)
                conn.sendmail(SMTP_USER, [to], msg.as_string())
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as conn:
                conn.starttls()
                conn.login(SMTP_USER, SMTP_PASS)
                conn.sendmail(SMTP_USER, [to], msg.as_string())
        return True
    except Exception as e:
        logger.exception("send_mail failed: %s", e)
        return False
