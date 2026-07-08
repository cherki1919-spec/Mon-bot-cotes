import requests
import time
from collections import defaultdict

# ========== CONFIGURATION ==========
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"
CHAT_ID = "810719713"
API_KEY = "38455300fddea39322e9debbe5c0ff76"
SPORT = "soccer"
REGIONS = "eu,us,au,uk"
MARKETS = "h2h"
SEUIL_BAISSE = -0.10  # Alerte pour baisse > 10%
# ===================================

# ---------- LISTE DES PAYS À SURVEILLER ----------
PAYS_CIBLES = {
    # EUROPE - 1ère Division
    "Malta", "Montenegro", "North Macedonia",
    # EUROPE - 2ème Division
    "Greece", "Cyprus", "Albania", "Georgia", "Kazakhstan", "Kosovo", "Slovenia",
    # EUROPE - 3ème Division
    "Austria", "Israel",
    # ASIE - 1ère Division
    "Bangladesh", "Mongolia", "Bhutan", "Myanmar", "Cambodia", "Malaysia",
    # ASIE - 2ème Division
    "India", "Thailand", "Indonesia", "Vietnam",
    # AMÉRIQUE LATINE - 1ère Division (Youth inclus)
    "Bolivia", "Panama", "Honduras", "Venezuela", "Jamaica",
    # AMÉRIQUE LATINE - 2ème Division
    "Costa Rica", "Paraguay", "Ecuador",
    # AMÉRIQUE LATINE - Divisions Mineures
    "Mexico", "Argentina", "Brazil"
}
# -------------------------------------------------

URL_ODDS = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"
PARAMS = {
    "apiKey": API_KEY,
    "regions": REGIONS,
    "markets": MARKETS
}

historique = defaultdict(lambda: {"home": 0.0, "draw": 0.0, "away": 0.0})

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"Erreur d'envoi : {e}")

print("🤖 Bot lancé - Surveillance des ligues ciblées...")

while True:
    try:
        reponse = requests.get(URL_ODDS, params=PARAMS, timeout=15)
        matchs = reponse.json()
        
        for match in matchs:
            # Extraction du pays depuis le nom de la compétition
            titre = match.get("sport_title", "")
            pays_match = None
            for pays in PAYS_CIBLES:
                if pays.lower() in titre.lower():
                    pays_match = pays
                    break
            
            # Si le pays n'est pas dans la liste, on ignore
            if not pays_match:
                continue
            
            id_match = match["id"]
            equipes = f"{match['home_team']} vs {match['away_team']}"
            
            # Récupération des cotes
            if not match.get("bookmakers"):
                continue
            bookmaker = match["bookmakers"][0]
            if not bookmaker.get("markets"):
                continue
            cotes = bookmaker["markets"][0]["outcomes"]
            cotes_actuelles = {c["name"]: c["price"] for c in cotes}
            
            home = cotes_actuelles.get("home", 0.0)
            draw = cotes_actuelles.get("draw", 0.0)
            away = cotes_actuelles.get("away", 0.0)
            
            anciennes = historique[id_match]
            # Si c'est la première vérification, on initialise sans alerte
            if anciennes["home"] == 0.0 and anciennes["draw"] == 0.0 and anciennes["away"] == 0.0:
                historique[id_match] = {"home": home, "draw": draw, "away": away}
                continue
            
            # Vérification des baisses (10%)
            if anciennes["home"] > 0:
                variation = (home - anciennes["home"]) / anciennes["home"]
                if variation < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE {pays_match}\n{equipes}\n"
                        f"🏠 {anciennes['home']:.2f} ➡️ {home:.2f} ({variation*100:.1f}%)"
                    )
            
            if anciennes["draw"] > 0:
                variation = (draw - anciennes["draw"]) / anciennes["draw"]
                if variation < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE {pays_match}\n{equipes}\n"
                        f"🤝 {anciennes['draw']:.2f} ➡️ {draw:.2f} ({variation*100:.1f}%)"
                    )
            
            if anciennes["away"] > 0:
                variation = (away - anciennes["away"]) / anciennes["away"]
                if variation < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE {pays_match}\n{equipes}\n"
                        f"✈️ {anciennes['away']:.2f} ➡️ {away:.2f} ({variation*100:.1f}%)"
                    )
            
            # Mise à jour de l'historique
            historique[id_match] = {"home": home, "draw": draw, "away": away}
        
        time.sleep(60)  # Vérification toutes les 60 secondes
        
    except Exception as e:
        print(f"Erreur : {e}")
        time.sleep(30)
