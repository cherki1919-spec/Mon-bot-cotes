import requests
import time
from collections import defaultdict

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"           # Ton token BotFather
CHAT_ID = "810719713"              # Ton ID Telegram
ISPORTS_API_KEY = "mRRgEBj54xLs8X9S"    # Clé iSports API
SEUIL_BAISSE = -0.10                  # -10%
CROWN_COMPANY_ID = "3"                # ID pour Crown
# =============================================================

# Pays à surveiller
PAYS_CIBLES = [
    "Cameroon", "Tunisia", "Algeria", "Malta", "Montenegro", "North Macedonia",
    "Greece", "Cyprus", "Albania", "Georgia", "Kazakhstan", "Kosovo", "Slovenia",
    "Austria", "Israel", "Bangladesh", "Mongolia", "Bhutan", "Myanmar",
    "Cambodia", "Malaysia", "India", "Thailand", "Indonesia", "Vietnam",
    "Bolivia", "Panama", "Honduras", "Venezuela", "Jamaica", "Costa Rica",
    "Paraguay", "Ecuador", "Mexico", "Argentina", "Brazil"
]

historique = defaultdict(lambda: {"home": 0.0, "draw": 0.0, "away": 0.0})

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("✅ Alerte envoyée")
    except Exception as e:
        print(f"❌ Erreur envoi: {e}")

def get_crown_odds():
    """Récupère les cotes en direct de Crown via iSports API"""
    url = "https://www.isportsapi.com/sport/football/odds/inplay"
    params = {
        "companyId": CROWN_COMPANY_ID,  # Filtrage sur Crown uniquement
        "apiKey": ISPORTS_API_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        return data.get("data", []) if data.get("code") == 200 else []
    except Exception as e:
        print(f"❌ Erreur API: {e}")
        return []

print("🤖 Bot lancé - Surveillance Crown via iSports API")

while True:
    try:
        matchs = get_crown_odds()
        print(f"📊 {len(matchs)} matchs Crown récupérés")

        matchs_filtres = []
        for match in matchs:
            # Vérification du pays
            pays = match.get("country", "")
            if pays in PAYS_CIBLES:
                # Extraction des cotes 1X2
                for update in match.get("updates", []):
                    if update.get("type") == 4:  # 4 = 1X2 [citation:9]
                        odds = {
                            "home": float(update.get("odds1", 0)),
                            "draw": float(update.get("odds2", 0)),
                            "away": float(update.get("odds3", 0))
                        }
                        matchs_filtres.append({
                            "id": match["matchId"],
                            "pays": pays,
                            "home": match.get("home", "?"),
                            "away": match.get("away", "?"),
                            "odds": odds
                        })
                        break

        print(f"🎯 {len(matchs_filtres)} matchs ciblés")

        for match in matchs_filtres:
            match_id = match["id"]
            home = match["odds"]["home"]
            draw = match["odds"]["draw"]
            away = match["odds"]["away"]

            if home == 0.0 and draw == 0.0 and away == 0.0:
                continue

            anciennes = historique[match_id]
            if anciennes["home"] == 0.0:
                historique[match_id] = {"home": home, "draw": draw, "away": away}
                print(f"📝 Init: {match['home']} vs {match['away']}")
                continue

            nom_match = f"{match['home']} vs {match['away']}"

            # Vérification des baisses
            if anciennes["home"] > 0 and home > 0:
                var = (home - anciennes["home"]) / anciennes["home"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE Crown ({match['pays']})\n{nom_match}\n"
                        f"🏠 {anciennes['home']:.2f} ➡️ {home:.2f} ({var*100:.1f}%)"
                    )

            if anciennes["draw"] > 0 and draw > 0:
                var = (draw - anciennes["draw"]) / anciennes["draw"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE Crown ({match['pays']})\n{nom_match}\n"
                        f"🤝 {anciennes['draw']:.2f} ➡️ {draw:.2f} ({var*100:.1f}%)"
                    )

            if anciennes["away"] > 0 and away > 0:
                var = (away - anciennes["away"]) / anciennes["away"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE Crown ({match['pays']})\n{nom_match}\n"
                        f"✈️ {anciennes['away']:.2f} ➡️ {away:.2f} ({var*100:.1f}%)"
                    )

            historique[match_id] = {"home": home, "draw": draw, "away": away}

        print("⏳ Pause 15 minutes...")
        time.sleep(900)  # 15 minutes

    except Exception as e:
        print(f"❌ Erreur: {e}")
        time.sleep(60)
