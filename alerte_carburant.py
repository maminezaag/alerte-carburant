"""
Surveillance du prix du carburant "Super" (ORLEN Bloherfelder Str. 126, Oldenburg)
Envoie un email si le prix atteint le seuil OU s'il a baissé depuis la dernière
vérification — et uniquement entre 6h et 21h, heure de Berlin.
"""

import os
import re
import sys
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

URL = "https://standorte.star.de/niedersachsen/oldenburg/bloherfelder-str.-126/581"
SEUIL = 2.3  # €/L

HEURE_DEBUT = 6   # 6h du matin, heure de Berlin
HEURE_FIN = 22    # 21h, heure de Berlin

EMAIL_EXPEDITEUR = os.environ["GMAIL_ADDRESS"]
EMAIL_MOT_DE_PASSE = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_DESTINATAIRE = os.environ["GMAIL_TO"]

FICHIER_ETAT = Path(__file__).parent / "dernier_etat_alerte.txt"


def dans_la_plage_horaire() -> bool:
    """Vérifie s'il est actuellement entre HEURE_DEBUT et HEURE_FIN à Berlin."""
    heure_berlin = datetime.now(ZoneInfo("Europe/Berlin")).hour
    return HEURE_DEBUT <= heure_berlin < HEURE_FIN


def recuperer_prix_super() -> float:
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(URL, headers=headers, timeout=15)
    resp.raise_for_status()
    texte = resp.text

    match = re.search(r"Super:\s*</?\w*>?\s*(\d+,\d+)\s*€", texte)
    if not match:
        match = re.search(r"\bSuper\s*:\s*(\d+,\d+)\s*€", texte)
    if not match:
        raise ValueError("Prix 'Super' introuvable sur la page.")

    return float(match.group(1).replace(",", "."))


def envoyer_email(prix: float, ancien_prix, seuil_atteint: bool, baisse: float):
    raisons = []
    if seuil_atteint:
        raisons.append(f"seuil de {SEUIL} € atteint")
    if baisse > 0 and ancien_prix is not None:
        raisons.append(f"baisse de {baisse:.3f} € depuis le dernier relevé ({ancien_prix:.3f} €)")
    if not raisons:
        raisons.append("premier relevé sous le seuil")

    msg = MIMEText(
        f"Le prix du Super à la station ORLEN Bloherfelder Str. 126 (Oldenburg) "
        f"est maintenant à {prix:.3f} €/L.\n\n"
        f"Raison(s) : {', '.join(raisons)}\n\n{URL}"
    )
    msg["Subject"] = f"Alerte carburant : Super à {prix:.3f} €"
    msg["From"] = EMAIL_EXPEDITEUR
    msg["To"] = EMAIL_DESTINATAIRE

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as serveur:
        serveur.login(EMAIL_EXPEDITEUR, EMAIL_MOT_DE_PASSE)
        serveur.send_message(msg)


def lire_dernier_prix():
    """Renvoie le dernier prix enregistré, ou None (premier lancement, ou ancien format)."""
    if FICHIER_ETAT.exists():
        contenu = FICHIER_ETAT.read_text().strip()
        try:
            return float(contenu)
        except ValueError:
            return None  # ancien fichier texte ("alerte_envoyee" etc.) : on repart à zéro
    return None


def ecrire_dernier_prix(prix: float):
    FICHIER_ETAT.write_text(f"{prix:.3f}")


def main():
    if not dans_la_plage_horaire():
        print(f"Hors plage horaire ({HEURE_DEBUT}h-{HEURE_FIN}h, heure de Berlin) — vérification ignorée.")
        return

    try:
        prix = recuperer_prix_super()
    except Exception as e:
        print(f"[ERREUR] Impossible de récupérer le prix : {e}")
        sys.exit(1)

    print(f"Prix Super actuel : {prix:.3f} €")

    dernier_prix = lire_dernier_prix()

    # --- Premier lancement ---
    if dernier_prix is None:
        if prix <= SEUIL:
            try:
                envoyer_email(prix, None, True, 0.0)
                print(f"Premier relevé sous le seuil ({prix:.3f} €) — email envoyé.")
            except Exception as e:
                print(f"[ERREUR] Envoi de l'email échoué : {e}")
                sys.exit(1)
        else:
            print(f"Premier relevé — {prix:.3f} € enregistré comme référence (au-dessus du seuil).")
        ecrire_dernier_prix(prix)
        return

    # --- Lancements suivants ---
    if prix >= dernier_prix:
        print(f"Prix inchangé ou en hausse ({prix:.3f} € vs {dernier_prix:.3f} €) — pas d'alerte.")
        return

    # Ici : le prix a baissé
    baisse = dernier_prix - prix
    seuil_atteint = prix <= SEUIL

    try:
        envoyer_email(prix, dernier_prix, seuil_atteint, baisse)
        print(f"Baisse détectée ({baisse:.3f} €) — email envoyé.")
    except Exception as e:
        print(f"[ERREUR] Envoi de l'email échoué : {e}")
        sys.exit(1)

    ecrire_dernier_prix(prix)


if __name__ == "__main__":
    main()
