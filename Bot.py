import requests
import time
from collections import defaultdict

# ========== CONFIGURATION ==========
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"
CHAT_ID = "810719713"
API_KEY = "38455300fddea39322e9debbe5c0ff76"
SPORT = "upcoming"  # ✅ Changement clé : "upcoming" couvre TOUS les sports et compétitions
REGIONS = "eu,us,au,uk"
MARKETS = "h2h"
SEUIL_BAISSE = -0.01  # Temporairement à 1% pour tester
# ===================================

# ✅ Liste des mots-clés (pays + variantes) pour une détection plus souple
MOTS_CLES = {
    "Malta", "Montenegro", "North Macedonia", "Macedonia", "Greece", "Cyprus", "Albania",
    "Georgia", "Kazakhstan", "Kosovo", "Slovenia", "Austria", "Israel",
    "Bangladesh", "Mongolia", "Bhutan", "Myanmar", "Cambodia", "Malaysia",
    "India", "Thailand", "Indonesia", "Vietnam", "Bolivia", "Panama",
    "Honduras", "Venezuela", "Jamaica", "Costa Rica", "Paraguay", "Ecuador",
    "Mexico", "Argentina", "Brazil", "Brasil"
}

URL_ODDS = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"
PARAMS = {"apiKey": API_KEY, "regions": REGIONS, "markets": MARKETS}
historique = defaultdict(lambda: {"home": 0.0, "draw": 0.0, "away": 0.0})

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("✅ Message envoyé à Telegram")
    except Exception as e:
        print(f"❌ Erreur d'envoi : {e}")

print("🤖 Bot lancé - Surveillance élargie...")

while True:
    try:
        reponse = requests.get(URL_ODDS, params=PARAMS, timeout=15)
        matchs = reponse.json()
        print(f"🔍 {len(matchs)} matchs reçus")

        for match in matchs:
            titre = match.get("sport_title", "")
            equipes = f"{match.get('home_team', '?')} vs {match.get('away_team', '?')}"

            # Vérification si le titre contient un de nos mots-clés
            pays_match = None
            for mot in MOTS_CLES:
                if mot.lower() in titre.lower():
                    pays_match = mot
                    break

            if not pays_match:
                # Affiche les 5 premiers matchs ignorés pour déboguer
                continue

            print(f"✅ Match ciblé : {titre} - {equipes}")

            # Récupération des cotes
            if not match.get("bookmakers"):
                print("❌ Aucun bookmaker")
                continue

            bookmaker = match["bookmakers"][0]
            if not bookmaker.get("markets"):
                print("❌ Aucun marché")
                continue

            cotes = bookmaker["markets"][0]["outcomes"]
            cotes_actuelles = {c["name"]: c["price"] for c in cotes}
            home = cotes_actuelles.get("home", 0.0)
            draw = cotes_actuelles.get("draw", 0.0)
            away = cotes_actuelles.get("away", 0.0)
            print(f"📊 Cotes : H={home} D={draw} A={away}")

            # Si les cotes sont à 0, on ignore ce match (pas de cotes disponibles)
            if home == 0.0 and draw == 0.0 and away == 0.0:
                print("⏳ Cotes non disponibles pour l'instant")
                continue

            anciennes = historique[match["id"]]
            if anciennes["home"] == 0.0 and anciennes["draw"] == 0.0 and anciennes["away"] == 0.0:
                historique[match["id"]] = {"home": home, "draw": draw, "away": away}
                print("📝 Première init")
                continue

            # Vérification des baisses
            if anciennes["home"] > 0 and home > 0:
                variation = (home - anciennes["home"]) / anciennes["home"]
                if variation < SEUIL_BAISSE:
                    envoyer_telegram(f"🔻 BAISSE {pays_match}\n{equipes}\n🏠 {anciennes['home']:.2f} ➡️ {home:.2f} ({variation*100:.1f}%)")

            if anciennes["draw"] > 0 and draw > 0:
                variation = (draw - anciennes["draw"]) / anciennes["draw"]
                if variation < SEUIL_BAISSE:
                    envoyer_telegram(f"🔻 BAISSE {pays_match}\n{equipes}\n🤝 {anciennes['draw']:.2f} ➡️ {draw:.2f} ({variation*100:.1f}%)")

            if anciennes["away"] > 0 and away > 0:
                variation = (away - anciennes["away"]) / anciennes["away"]
                if variation < SEUIL_BAISSE:
                    envoyer_telegram(f"🔻 BAISSE {pays_match}\n{equipes}\n✈️ {anciennes['away']:.2f} ➡️ {away:.2f} ({variation*100:.1f}%)")

            historique[match["id"]] = {"home": home, "draw": draw, "away": away}

        time.sleep(60)
    except Exception as e:
        print(f"❌ Erreur : {e}")
        time.sleep(30)
