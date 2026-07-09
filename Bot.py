import requests
import time
from datetime import datetime
from collections import defaultdict

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"                # Ton token BotFather
CHAT_ID = "810719713"                    # Ton ID Telegram
ODDS_API_KEY = "a81c1c5a671c6f3082dfd2fc65d2db11546154b0ba427abaefbe7b13458efdbd"          # Ta clé Odds-API.io
SEUIL_BAISSE = -0.10                       # -10% (met -0.01 pour tester)
# =============================================================

PAYS_CIBLES = {
    "Cameroon", "Tunisia", "Algeria", "Malta", "Montenegro", "North Macedonia",
    "Greece", "Cyprus", "Albania", "Georgia", "Kazakhstan", "Kosovo", "Slovenia",
    "Austria", "Israel", "Bangladesh", "Mongolia", "Bhutan", "Myanmar",
    "Cambodia", "Malaysia", "India", "Thailand", "Indonesia", "Vietnam",
    "Bolivia", "Panama", "Honduras", "Venezuela", "Jamaica", "Costa Rica",
    "Paraguay", "Ecuador", "Mexico", "Argentina", "Brazil"
}

# Configuration Odds-API.io
URL_BASE = "https://api.odds-api.net/v1"
HEADERS = {"X-API-Key": ODDS_API_KEY}

historique = defaultdict(lambda: {"home": 0.0, "draw": 0.0, "away": 0.0})

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("✅ Alerte envoyée !")
    except Exception as e:
        print(f"❌ Erreur d'envoi : {e}")

def get_fixtures_du_jour():
    """Récupère les matchs du jour depuis Odds-API.io"""
    url = f"{URL_BASE}/events"
    params = {
        "sport": "soccer",
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    try:
        reponse = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = reponse.json()
        
        # Vérification du format de réponse
        if not isinstance(data, list):
            print(f"⚠️ Réponse inattendue : {data}")
            return []
        return data
    except Exception as e:
        print(f"❌ Erreur fixtures : {e}")
        return []

def get_odds_pour_match(event_id):
    """Récupère les cotes pour un match spécifique"""
    url = f"{URL_BASE}/events/{event_id}/odds"
    try:
        reponse = requests.get(url, headers=HEADERS, timeout=15)
        data = reponse.json()
        
        if not data or not isinstance(data, dict):
            return None
        
        # Recherche du marché 1X2
        for market in data.get("markets", []):
            if market.get("name") == "1X2":
                outcomes = market.get("outcomes", [])
                if len(outcomes) >= 3:
                    home = float(outcomes[0].get("price", 0))
                    draw = float(outcomes[1].get("price", 0))
                    away = float(outcomes[2].get("price", 0))
                    return {"home": home, "draw": draw, "away": away}
        return None
    except Exception as e:
        print(f"⚠️ Erreur cotes {event_id} : {e}")
        return None

print("🤖 Bot lancé - Odds-API.io (surveillance élargie)")

while True:
    try:
        fixtures = get_fixtures_du_jour()
        print(f"📊 {len(fixtures)} matchs aujourd'hui")

        # Filtrer les matchs par pays
        matches_a_surveiller = []
        for match in fixtures:
            pays = match.get("country", "")
            if pays in PAYS_CIBLES:
                matches_a_surveiller.append({
                    "id": match.get("id"),
                    "pays": pays,
                    "home": match.get("home_team", "?"),
                    "away": match.get("away_team", "?")
                })

        print(f"🎯 {len(matches_a_surveiller)} matchs à surveiller")

        for match_info in matches_a_surveiller:
            fixture_id = match_info["id"]
            if not fixture_id:
                continue
                
            cotes = get_odds_pour_match(fixture_id)
            if not cotes:
                continue

            home, draw, away = cotes["home"], cotes["draw"], cotes["away"]
            if home == 0.0 and draw == 0.0 and away == 0.0:
                continue

            anciennes = historique[fixture_id]
            if anciennes["home"] == 0.0 and anciennes["draw"] == 0.0 and anciennes["away"] == 0.0:
                historique[fixture_id] = {"home": home, "draw": draw, "away": away}
                print(f"📝 Init : {match_info['home']} vs {match_info['away']} ({match_info['pays']})")
                continue

            nom_match = f"{match_info['home']} vs {match_info['away']}"
            pays = match_info['pays']

            # Vérification des baisses
            if anciennes["home"] > 0 and home > 0:
                var = (home - anciennes["home"]) / anciennes["home"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE ({pays})\n{nom_match}\n"
                        f"🏠 {anciennes['home']:.2f} ➡️ {home:.2f} ({var*100:.1f}%)"
                    )

            if anciennes["draw"] > 0 and draw > 0:
                var = (draw - anciennes["draw"]) / anciennes["draw"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE ({pays})\n{nom_match}\n"
                        f"🤝 {anciennes['draw']:.2f} ➡️ {draw:.2f} ({var*100:.1f}%)"
                    )

            if anciennes["away"] > 0 and away > 0:
                var = (away - anciennes["away"]) / anciennes["away"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(
                        f"🔻 BAISSE ({pays})\n{nom_match}\n"
                        f"✈️ {anciennes['away']:.2f} ➡️ {away:.2f} ({var*100:.1f}%)"
                    )

            historique[fixture_id] = {"home": home, "draw": draw, "away": away}

        # Pause de 5 minutes (300 secondes) pour respecter le quota
        print("⏳ Pause de 5 minutes...")
        time.sleep(300)  # 5 minutes = 300 secondes

    except Exception as e:
        print(f"❌ Erreur générale : {e}")
        time.sleep(60)
