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
SEUIL_BAISSE = -0.01  # Temporairement à 1% pour tester
# ===================================

PAYS_CIBLES = {
    "Malta", "Montenegro", "North Macedonia", "Greece", "Cyprus", "Albania",
    "Georgia", "Kazakhstan", "Kosovo", "Slovenia", "Austria", "Israel",
    "Bangladesh", "Mongolia", "Bhutan", "Myanmar", "Cambodia", "Malaysia",
    "India", "Thailand", "Indonesia", "Vietnam", "Bolivia", "Panama",
    "Honduras", "Venezuela", "Jamaica", "Costa Rica", "Paraguay", "Ecuador",
    "Mexico", "Argentina", "Brazil"
}

URL_ODDS = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"
PARAMS = {"apiKey": API_KEY, "regions": REGIONS, "markets": MARKETS}
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
        print(f"🔍 {len(matchs)} matchs reçus de l'API")  # LOG 1

        for match in matchs:
            titre = match.get("sport_title", "")
            print(f"📋 Match : {titre}")  # LOG 2

            pays_match = None
            for pays in PAYS_CIBLES:
                if pays.lower() in titre.lower():
                    pays_match = pays
                    break

            if not pays_match:
                print(f"⏭️ Pays non reconnu pour : {titre}")  # LOG 3
                continue

            print(f"✅ Pays détecté : {pays_match} pour {titre}")  # LOG 4

            if not match.get("bookmakers"):
                print("❌ Pas de bookmaker pour ce match")
                continue

            bookmaker = match["bookmakers"][0]
            if not bookmaker.get("markets"):
                print("❌ Pas de marché pour ce match")
                continue

            cotes = bookmaker["markets"][0]["outcomes"]
            cotes_actuelles = {c["name"]: c["price"] for c in cotes}
            home = cotes_actuelles.get("home", 0.0)
            draw = cotes_actuelles.get("draw", 0.0)
            away = cotes_actuelles.get("away", 0.0)
            print(f"📊 Cotes : H={home} D={draw} A={away}")  # LOG 5

            # Ici on vérifie si on a déjà des anciennes cotes
            anciennes = historique[match["id"]]
            if anciennes["home"] == 0.0 and anciennes["draw"] == 0.0 and anciennes["away"] == 0.0:
                historique[match["id"]] = {"home": home, "draw": draw, "away": away}
                print("📝 Première init, on enregistre")  # LOG 6
                continue

            # Vérification des baisses
            if anciennes["home"] > 0 and home > 0:
                variation = (home - anciennes["home"]) / anciennes["home"]
                if variation < SEUIL_BAISSE:
                    envoyer_telegram(f"🔻 BAISSE {pays_match}\n{match['home_team']} vs {match['away_team']}\n🏠 {anciennes['home']:.2f} ➡️ {home:.2f} ({variation*100:.1f}%)")
                    print(f"🚨 Alerte envoyée pour home !")  # LOG 7
            # (idem pour draw et away, je raccourcis ici mais garde la même logique)

        time.sleep(60)
    except Exception as e:
        print(f"❌ Erreur générale : {e}")
        time.sleep(30)
