import os
import smtplib
from email.message import EmailMessage

EMAIL_EXPEDITEUR = os.environ["GMAIL_ADDRESS"]
EMAIL_MOT_DE_PASSE = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_DESTINATAIRE = os.environ["GMAIL_TO"]

msg = EmailMessage()
msg["From"] = EMAIL_EXPEDITEUR
msg["To"] = EMAIL_DESTINATAIRE
msg["Subject"] = "[job-bot] test OK"
msg.set_content(
    "Si tu lis ce mail, le pipeline GitHub Actions fonctionne.\n"
    "Prochaine étape : la collecte des offres."
)

with smtplib.SMTP("smtp.gmail.com", 587) as s:
    s.starttls()
    s.login(EMAIL_EXPEDITEUR, EMAIL_MOT_DE_PASSE)
    s.send_message(msg)

print("E-mail envoyé à", EMAIL_DESTINATAIRE)
