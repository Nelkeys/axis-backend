import requests
from app.config import settings

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """Send via Brevo HTTP API. No SMTP port or IP restrictions."""
    try:
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": settings.brevo_api_key,
        }
        payload = {
            "sender": {"name": "AxisEdu", "email": settings.email_sender_address},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_body,
        }
        response = requests.post(BREVO_API_URL, json=payload, headers=headers, timeout=10)
        
        # Log the full response for debugging
        print(f"Brevo API response: {response.status_code}")
        print(f"Brevo API body: {response.text}")
        
        if response.status_code in (200, 201):
            return True
        
        # Non-success status codes
        print(f"Brevo API error {response.status_code}: {response.text}")
        return False
    except Exception as e:
        print(f"Email failed to send: {e}")
        return False


def send_partner_invite_email(to_email: str, code: str) -> bool:
    link = f"{settings.frontend_url}/become-partner?code={code}"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto;padding:24px;border:1px solid #eee;">
      <h2 style="color:#1B2430;">You're invited to become a Raven Partner</h2>
      <p>Hi,</p>
      <p>You've been selected to earn <strong>5% cash commission</strong> on every course purchase made by students you invite.</p>
      <p style="font-size:14px;color:#555;">Your invite code:</p>
      <p style="font-size:22px;font-family:monospace;letter-spacing:2px;background:#f5f5f5;padding:12px;border-radius:8px;display:inline-block;">{code}</p>
      <p><a href="{link}" style="background:#1B2430;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;">Accept Invitation</a></p>
      <p style="font-size:13px;color:#777;">You'll need a Raven student account first. After signing up, paste the code on the Become a Partner page.</p>
    </div>
    """
    return send_email(to_email, "You're invited to become a Raven Partner", html)