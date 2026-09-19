"""
Surveillance du prix du carburant "Super" (ORLEN Bloherfelder Str. 126, Oldenburg)
Envoie un email si le prix est <= au seuil défini.
 
Conçu pour être lancé périodiquement par le Planificateur de tâches Windows
(le script fait UNE vérification puis se termine).
"""
 
import re
import sys
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
import os
import requests
 
# --- Configuration ---
URL = "https://standorte.star.de/niedersachsen/oldenburg/bloherfelder-str.-126/581"
SEUIL = 2.3  # €/L - envoie une alerte si le prix Super est <= à cette valeur
 
EMAIL_EXPEDITEUR = os.environ["GMAIL_ADDRESS"]
EMAIL_MOT_DE_PASSE = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_DESTINATAIRE = os.environ["GMAIL_TO"]

# Fichier utilisé pour ne pas ré-envoyer un email à chaque vérification
# tant que le prix reste sous le seuil (sinon: un email toutes les 10 min)
FICHIER_ETAT = Path(__file__).parent / "dernier_etat_alerte.txt"
 
 
def recuperer_prix_super() -> float:
    """Récupère le prix du Super depuis la page de la station."""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(URL, headers=headers, timeout=15)
    resp.raise_for_status()
    texte = resp.text
 
    # On cible précisément "Super:" pour éviter "Super Plus:" et "Super E10:"
    match = re.search(r"Super:\s*</?\w*>?\s*(\d+,\d+)\s*€", texte)
    if not match:
        # Repli : chercher sans balises HTML (au cas où la structure change)
        match = re.search(r"\bSuper\s*:\s*(\d+,\d+)\s*€", texte)
 
    if not match:
        raise ValueError("Prix 'Super' introuvable sur la page — la structure du site a peut-être changé.")
 
    prix_str = match.group(1).replace(",", ".")
    return float(prix_str)
 
 
def envoyer_email(prix: float):
    msg = MIMEText(
        f"Le prix du Super à la station ORLEN Bloherfelder Str. 126 (Oldenburg) "
        f"est descendu à {prix:.3f} €/L (seuil : {SEUIL} €/L).\n\n{URL}"
    )
    msg["Subject"] = f"Alerte carburant : Super à {prix:.3f} €"
    msg["From"] = EMAIL_EXPEDITEUR
    msg["To"] = EMAIL_DESTINATAIRE
 
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
        serveur.login(EMAIL_EXPEDITEUR, EMAIL_MOT_DE_PASSE)
        serveur.send_message(msg)
 
 
def lire_dernier_etat() -> str:
    if FICHIER_ETAT.exists():
        return FICHIER_ETAT.read_text().strip()
    return ""
 
 
def ecrire_etat(etat: str):
    FICHIER_ETAT.write_text(etat)
 
 
def main():
    try:
        prix = recuperer_prix_super()
    except Exception as e:
        print(f"[ERREUR] Impossible de récupérer le prix : {e}")
        sys.exit(1)
 
    print(f"Prix Super actuel : {prix:.3f} €")
 
    seuil_atteint = prix <= SEUIL
    dernier_etat = lire_dernier_etat()
 
    if seuil_atteint and dernier_etat != "alerte_envoyee":
        try:
            envoyer_email(prix)
            print("Email envoyé.")
            ecrire_etat("alerte_envoyee")
        except Exception as e:
            print(f"[ERREUR] Envoi de l'email échoué : {e}")
            sys.exit(1)
    elif not seuil_atteint:
        # Le prix est remonté au-dessus du seuil : on réarme l'alerte
        # pour qu'un nouveau passage sous le seuil déclenche un nouvel email
        ecrire_etat("au_dessus_du_seuil")
    else:
        print("Seuil déjà atteint, email déjà envoyé précédemment. Pas de nouvel envoi.")
 
 
if __name__ == "__main__":
    main()
