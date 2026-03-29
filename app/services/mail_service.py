"""
app/services/mail_service.py — Email delivery for CORE OS.

Production:  SMTP required. Missing config raises RuntimeError at startup
             (caught by startup_checks.py before this code ever runs).
             Runtime send failures log the error and return False — the
             caller must handle this and show the user a meaningful message.

Development: If MAIL_SERVER is not set, the reset URL is printed to the
             console (stderr) so developers can test without SMTP.
"""
import smtplib
import os
import logging
from email.mime.text      import MIMEText
from email.mime.multipart import MIMEMultipart

log = logging.getLogger(__name__)


def _smtp_config() -> dict:
    return {
        'server':   os.environ.get('MAIL_SERVER', ''),
        'port':     int(os.environ.get('MAIL_PORT', 587)),
        'username': os.environ.get('MAIL_USERNAME', ''),
        'password': os.environ.get('MAIL_PASSWORD', ''),
        'use_tls':  os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
        'from_addr': os.environ.get('MAIL_FROM',
                      os.environ.get('MAIL_USERNAME', 'noreply@coreos.app')),
    }


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """
    Send a password reset email.

    Returns True on success.
    Returns False on failure after logging the error.

    In development without SMTP: prints the URL to console and returns False.
    The caller (auth route) checks the return value and shows a dev-mode message.
    """
    cfg = _smtp_config()

    if not cfg['server']:
        # Development fallback — console output only
        import sys
        env = os.environ.get('FLASK_ENV', 'development')
        if env == 'production':
            # startup_checks should have caught this — log as critical
            log.critical(
                'MAIL_SERVER not set in production. '
                'Password reset URL for %s: %s', to_email, reset_url
            )
        else:
            print(
                f'\n[CORE OS DEV] Password reset URL for {to_email}:\n'
                f'  {reset_url}\n',
                file=sys.stderr,
            )
        return False

    subject = 'CORE OS — Password Reset Request'

    body_text = (
        'CORE OS — PASSWORD RESET PROTOCOL\n\n'
        'A reset was requested for this operative account.\n\n'
        f'Reset link (valid for 1 hour):\n{reset_url}\n\n'
        'If you did not request this, ignore this message.\n'
        'Your password will not change until you visit the link above.\n\n'
        '— CORE OS Security System'
    )

    body_html = f"""<!DOCTYPE html>
<html>
<body style="background:#050810;color:#e2e8f0;font-family:monospace;padding:40px;">
<div style="max-width:500px;margin:0 auto;background:rgba(99,102,241,0.06);
     border:1px solid rgba(99,102,241,0.25);border-radius:12px;padding:32px;">
  <div style="font-family:sans-serif;font-size:1.6rem;font-weight:700;
       letter-spacing:4px;color:#e2e8f0;margin-bottom:8px;">
    CORE <span style="color:#6366f1;">OS</span>
  </div>
  <div style="font-size:0.65rem;color:#64748b;letter-spacing:3px;
       margin-bottom:28px;">PASSWORD_RESET_PROTOCOL</div>
  <p style="color:#94a3b8;font-size:0.85rem;line-height:1.8;margin-bottom:24px;">
    A reset request was received for this operative account.<br>
    Link expires in <strong style="color:#22d3ee;">1 hour</strong>.
  </p>
  <a href="{reset_url}"
     style="display:block;background:linear-gradient(135deg,#6366f1,#4f46e5);
            color:#fff;text-decoration:none;padding:14px 24px;border-radius:10px;
            font-weight:700;letter-spacing:2px;text-align:center;
            font-family:sans-serif;font-size:0.9rem;">
    RESET PASSWORD
  </a>
  <p style="color:#475569;font-size:0.7rem;margin-top:24px;line-height:1.6;">
    If you did not request this, ignore this message.<br>
    Your password will not change.
  </p>
</div>
</body>
</html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = cfg['from_addr']
    msg['To']      = to_email
    msg.attach(MIMEText(body_text, 'plain'))
    msg.attach(MIMEText(body_html, 'html'))

    try:
        with smtplib.SMTP(cfg['server'], cfg['port'], timeout=10) as smtp:
            if cfg['use_tls']:
                smtp.starttls()
            if cfg['username']:
                smtp.login(cfg['username'], cfg['password'])
            smtp.sendmail(cfg['from_addr'], [to_email], msg.as_string())
        log.info('Password reset email sent to %s', to_email)
        return True

    except smtplib.SMTPAuthenticationError:
        log.error('SMTP authentication failed for user %s', cfg['username'])
        return False
    except smtplib.SMTPConnectError:
        log.error('Cannot connect to SMTP server %s:%s', cfg['server'], cfg['port'])
        return False
    except smtplib.SMTPException as exc:
        log.error('SMTP error sending to %s: %s', to_email, exc)
        return False
    except OSError as exc:
        log.error('Network error sending email to %s: %s', to_email, exc)
        return False
