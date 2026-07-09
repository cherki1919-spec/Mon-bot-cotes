import requests
import time
from datetime import datetime
from collections import defaultdict

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"
CHAT_ID = "810719713"
RAPIDAPI_KEY = "da61753fdd0448298657e6e316007677"
SEUIL_BAISSE = -0.01                  # -10% (met -0.01 pour tester)
# =============================================================

# ---------- Liste des pays à surveiller ----------
PAYS_CIBLES = {
    # Afrique
    "Cameroon", "Tunisia", "Algeria",
    # Europe
    "Malta", "Montenegro", "North Macedonia", "Greece", "Cyprus", "Albania",
    "Georgia", "Kazakhstan", "Kosovo", "Slovenia", "Austria", "Israel",
    # Asie
    "Bangladesh", "Mongolia", "Bhutan", "Myanmar", "Cambodia", "Malaysia",
    "India", "Thailand", "Indonesia", "Vietnam",
    # Amérique Latine
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
    """Récupère les matchs du jour avec gestion d'erreur renforcée"""
    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")
    url = f"{URL_BASE}/fixtures"
    params = {"date": date_aujourdhui}
    try:
        reponse = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = reponse.json()
        
        # 🔍 Si l'API renvoie une erreur (ex: limit exceeded), on l'affiche
        if not isinstance(data, dict):
            print(f"⚠️ Réponse inattendue (type {type(data)}) : {data}")
            return []
        
        if data.get("errors"):
            print(f"❌ Erreur API : {data['errors']}")
            return []
        
        if data.get("results", 0) == 0:
            print("📭 Aucun match trouvé pour aujourd'hui.")
            return []
        
        # Vérification que "response" est bien une liste
        response = data.get("response")
        if not isinstance(response, list):
            print(f"⚠️ 'response' n'est pas une liste : {type(response)}")
            return []
        
        return response
    except Exception as e:
        print(f"❌ Erreur fixtures : {e}")
        return []

def get_odds_pour_fixture(fixture_id):
    """Récupère les cotes pour un match spécifique"""
    url = f"{URL_BASE}/odds"
    params = {"fixture": fixture_id}
    try:
        reponse = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = reponse.json()
        
        if not isinstance(data, dict) or data.get("results", 0) == 0:
            return None
        
        response = data.get("response")
        if not response or not isinstance(response, list) or len(response) == 0:
            return None
        
        bookmakers = response[0].get("bookmakers", [])
        if not bookmakers:
            return None
        
        for bet in bookmakers[0].get("bets", []):
            if bet.get("id") == 1 or bet.get("name") == "Match Winner":
                valeurs = bet.get("values", [])
                if len(valeurs) >= 3:
                    try:
                        home = float(valeurs[0].get("odd", 0))
                        draw = float(valeurs[1].get("odd", 0))
                        away = float(valeurs[2].get("odd", 0))
                        return {"home": home, "draw": draw, "away": away}
                    except (ValueError, TypeError):
                        return None
        return None
    except Exception as e:
        print(f"⚠️ Erreur cotes {fixture_id} : {e}")
        return None

print("🤖 Bot lancé - Surveillance élargie (robuste)")

while True:
    try:
        fixtures = get_fixtures_du_jour()
        print(f"📊 {len(fixtures)} matchs aujourd'hui")

        # Filtrer les matchs par pays (avec vérification de sécurité)
        matches_a_surveiller = []
        for match in fixtures:
            # Vérifier que match est un dictionnaire
            if not isinstance(match, dict):
                print(f"⚠️ Élément ignoré (non-dict) : {match}")
                continue
            
            # Extraction sécurisée du pays
            league = match.get("league", {})
            if not isinstance(league, dict):
                continue
            pays = league.get("country", "")
            
            if pays in PAYS_CIBLES:
                # Extraction sécurisée des équipes
                teams = match.get("teams", {})
                if not isinstance(teams, dict):
                    continue
                home_team = teams.get("home", {}).get("name", "?") if isinstance(teams.get("home"), dict) else "?"
                away_team = teams.get("away", {}).get("name", "?") if isinstance(teams.get("away"), dict) else "?"
                
                fixture = match.get("fixture", {})
                if not isinstance(fixture, dict):
                    continue
                fixture_id = fixture.get("id")
                
                if fixture_id:
                    matches_a_surveiller.append({
                        "id": fixture_id,
                        "pays": pays,
                        "home": home_team,
                        "away": away_team
                    })

        print(f"🎯 {len(matches_a_surveiller)} matchs à surveiller")

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
                print(f"📝 Init : {match_info['home']} vs {match_info['away']} ({match_info['pays']})")
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

        print("⏳ Pause de 1 heure...")
        time.sleep(3600)

    except Exception as e:
        print(f"❌ Erreur générale : {e}")
        time.sleep(60)
