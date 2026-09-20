"""TEST : récupère le prix du Super et envoie un email à chaque appel.
Sert uniquement à valider la chaîne cron-job.org → GitHub → email."""

import os
import re
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

URL = "https://standorte.star.de/niedersachsen/oldenburg/bloherfelder-str.-126/581"

EMAIL_EXPEDITEUR = os.environ["GMAIL_ADDRESS"]
EMAIL_MOT_DE_PASSE = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_DESTINATAIRE = os.environ["GMAIL_TO"]


def recuperer_prix_super() -> float:
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    resp.raise_for_status()
    match = re.search(r"Super:\s*</?\w*>?\s*(\d+,\d+)\s*€", resp.text)
    if not match:
        match = re.search(r"\bSuper\s*:\s*(\d+,\d+)\s*€", resp.text)
    if not match:
        raise ValueError("Prix 'Super' introuvable sur la page.")
    return float(match.group(1).replace(",", "."))


prix = recuperer_prix_super()
maintenant = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d/%m/%Y à %H:%M:%S")

msg = MIMEText(
    f"✅ Test réussi !\n\n"
    f"Prix du Super : {prix:.3f} €/L\n"
    f"Relevé le {maintenant} (heure de Berlin)\n\n"
    f"Station : {URL}"
)
msg["Subject"] = f"[TEST] Super à {prix:.3f} € — {maintenant}"
msg["From"] = EMAIL_EXPEDITEUR
msg["To"] = EMAIL_DESTINATAIRE

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
    serveur.login(EMAIL_EXPEDITEUR, EMAIL_MOT_DE_PASSE)
    serveur.send_message(msg)

print(f"Email de test envoyé — Super à {prix:.3f} € ({maintenant})")
