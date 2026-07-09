import requests
import time
from datetime import datetime
from collections import defaultdict

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"
CHAT_ID = "810719713"
RAPIDAPI_KEY = "da61753fdd0448298657e6e316007677"
SEUIL_BAISSE = -0.01                  # -10% (met -0.01 pour tester)
# =============================================================

# ---------- Liste des pays à surveiller (MISE À JOUR) ----------
PAYS_CIBLES = {
    # Afrique (Nouveaux)
    "Cameroon", "Tunisia", "Algeria",
    # Europe
    "Malta", "Montenegro", "North Macedonia", "Greece", "Cyprus", "Albania",
    "Georgia", "Kazakhstan", "Kosovo", "Slovenia", "Austria", "Israel",
    # Asie
    "Bangladesh", "Mongolia", "Bhutan", "Myanmar", "Cambodia", "Malaysia",
    "India", "Thailand", "Indonesia", "Vietnam",
    # Amérique Latine (Bolivie, Équateur, Paraguay déjà présents)
    "Bolivia", "Panama", "Honduras", "Venezuela", "Jamaica",
    "Costa Rica", "Paraguay", "Ecuador",
    "Mexico", "Argentina", "Brazil"
}

# Configuration de l'API Football
URL_BASE = "https://api-football-v1.p.rapidapi.com/v3"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

historique = defaultdict(lambda: {"home": 0.0, "draw": 0.0, "away": 0.0})

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("✅ Alerte envoyée !")
    except Exception as e:
        print(f"❌ Erreur d'envoi : {e}")

def get_fixtures_du_jour():
    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")
    url = f"{URL_BASE}/fixtures"
    params = {"date": date_aujourdhui}
    try:
        reponse = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = reponse.json()
        if data.get("results", 0) == 0:
            print("📭 Aucun match trouvé pour aujourd'hui.")
            return []
        return data.get("response", [])
    except Exception as e:
        print(f"❌ Erreur fixtures : {e}")
        return []

def get_odds_pour_fixture(fixture_id):
    url = f"{URL_BASE}/odds"
    params = {"fixture": fixture_id}
    try:
        reponse = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = reponse.json()
        if data.get("results", 0) == 0:
            return None
        bookmakers = data["response"][0].get("bookmakers", [])
        if not bookmakers:
            return None
        for bet in bookmakers[0].get("bets", []):
            if bet.get("id") == 1 or bet.get("name") == "Match Winner":
                valeurs = bet.get("values", [])
                if len(valeurs) >= 3:
                    home = float(valeurs[0].get("odd", 0))
                    draw = float(valeurs[1].get("odd", 0))
                    away = float(valeurs[2].get("odd", 0))
                    return {"home": home, "draw": draw, "away": away}
        return None
    except Exception as e:
        print(f"⚠️ Erreur cotes {fixture_id} : {e}")
        return None

print("🤖 Bot lancé - Surveillance élargie (Afrique + AmLat + Asie + Europe)")

while True:
    try:
        fixtures = get_fixtures_du_jour()
        print(f"📊 {len(fixtures)} matchs aujourd'hui")

        matches_a_surveiller = []
        for match in fixtures:
            pays = match.get("league", {}).get("country", "")
            if pays in PAYS_CIBLES:
                matches_a_surveiller.append({
                    "id": match["fixture"]["id"],
                    "pays": pays,
                    "home": match["teams"]["home"]["name"],
                    "away": match["teams"]["away"]["name"]
                })

        print(f"🎯 {len(matches_a_surveiller)} matchs à surveiller (filtre pays)")

        for match_info in matches_a_surveiller:
            fixture_id = match_info["id"]
            cotes = get_odds_pour_fixture(fixture_id)
            if not cotes:
                continue

            home, draw, away = cotes["home"], cotes["draw"], cotes["away"]
            if home == 0.0 and draw == 0.0 and away == 0.0:
                continue

            anciennes = historique[fixture_id]
            if anciennes["home"] == 0.0 and anciennes["draw"] == 0.0 and anciennes["away"] == 0.0:
                historique[fixture_id] = {"home": home, "draw": draw, "away": away}
                print(f"📝 Init : {match_info['home']} vs {match_info['away']}")
                continue

            nom_match = f"{match_info['home']} vs {match_info['away']}"
            pays = match_info['pays']

            if anciennes["home"] > 0 and home > 0:
                var = (home - anciennes["home"]) / anciennes["home"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(f"🔻 BAISSE ({pays})\n{nom_match}\n🏠 {anciennes['home']:.2f} ➡️ {home:.2f} ({var*100:.1f}%)")

            if anciennes["draw"] > 0 and draw > 0:
                var = (draw - anciennes["draw"]) / anciennes["draw"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(f"🔻 BAISSE ({pays})\n{nom_match}\n🤝 {anciennes['draw']:.2f} ➡️ {draw:.2f} ({var*100:.1f}%)")

            if anciennes["away"] > 0 and away > 0:
                var = (away - anciennes["away"]) / anciennes["away"]
                if var < SEUIL_BAISSE:
                    envoyer_telegram(f"🔻 BAISSE ({pays})\n{nom_match}\n✈️ {anciennes['away']:.2f} ➡️ {away:.2f} ({var*100:.1f}%)")

            historique[fixture_id] = {"home": home, "draw": draw, "away": away}

        # ✅ Pause de 1 heure (3600s) pour respecter le quota gratuit (100 appels/jour)
        print("⏳ Pause de 1 heure...")
        time.sleep(3600)

    except Exception as e:
        print(f"❌ Erreur générale : {e}")
        time.sleep(60)
