import requests
import time
import random
from collections import defaultdict
from datetime import datetime

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"
  # Remplace par ton token BotFather
CHAT_ID = "810719713"       # Remplace par ton ID Telegram
SEUIL_DANGER_1MT = 2          # Seuil pour alerte 1ère MT
SEUIL_DANGER_MATCH = 2        # Seuil pour alerte match complet

# ==== TOUTES LES LIGUES ====
LEAGUE_SLUGS = [
    "eng.1", "eng.2", "eng.3", "eng.4",
    "esp.1", "esp.2",
    "ger.1", "ger.2",
    "ita.1", "ita.2",
    "fra.1", "fra.2",
    "usa.1",
    "mex.1",
    "bra.1", "bra.2",
    "arg.1",
    "uefa.champions",
    "uefa.europa",
]
# =============================================================

historique = defaultdict(lambda: {
    "danger_score": 0,
    "last_alert": 0,
    "home_shots": 0,
    "away_shots": 0,
    "home_corners": 0,
    "away_corners": 0,
    "home_possession": 0,
    "away_possession": 0,
    "home_shots_on_target": 0,
    "away_shots_on_target": 0,
    "home_attacks": 0,
    "away_attacks": 0,
    "last_alert_1mt": 0,
    "last_alert_match": 0
})

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("✅ Alerte envoyée")
        return True
    except Exception as e:
        print(f"❌ Erreur envoi: {e}")
        return False

def get_live_matches():
    """Récupère les matchs en direct (simule les stats pour test)"""
    all_matches = []
    base_url = "https://site.api.espn.com/apis/site/v2/sports/soccer"
    
    for league_slug in LEAGUE_SLUGS:
        try:
            url = f"{base_url}/{league_slug}/scoreboard"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if "events" not in data or len(data["events"]) == 0:
                continue
            
            for event in data["events"]:
                competition = event.get("competitions", [{}])[0]
                competitors = competition.get("competitors", [])
                
                if len(competitors) < 2:
                    continue
                
                home_team = competitors[0].get("team", {}).get("displayName", "?")
                away_team = competitors[1].get("team", {}).get("displayName", "?")
                home_score = int(competitors[0].get("score", 0))
                away_score = int(competitors[1].get("score", 0))
                event_id = event.get("id")
                
                minute = 0
                status = event.get("status", {})
                if status.get("type", {}).get("name") == "in":
                    clock = status.get("displayClock", "0:00")
                    if ":" in clock:
                        try:
                            minute = int(clock.split(":")[0])
                        except:
                            minute = 0
                
                # 🔥 SIMULATION DE STATISTIQUES (pour test)
                # Génère des stats aléatoires pour déclencher des alertes
                home_shots = random.randint(0, 8)
                away_shots = random.randint(0, 8)
                home_corners = random.randint(0, 5)
                away_corners = random.randint(0, 5)
                home_possession = random.randint(30, 70)
                away_possession = 100 - home_possession
                home_attacks = random.randint(0, 15)
                away_attacks = random.randint(0, 15)
                home_shots_on_target = random.randint(0, min(5, home_shots))
                away_shots_on_target = random.randint(0, min(5, away_shots))
                
                # Calcul du danger 1MT
                danger_score_1mt = 0
                if minute < 45:
                    if home_shots >= 2: danger_score_1mt += 2
                    if away_shots >= 2: danger_score_1mt += 2
                    if home_corners >= 2: danger_score_1mt += 1
                    if away_corners >= 2: danger_score_1mt += 1
                    if home_attacks >= 5: danger_score_1mt += 2
                    if away_attacks >= 5: danger_score_1mt += 2
                    if home_possession > 60: danger_score_1mt += 1
                    if away_possession > 60: danger_score_1mt += 1
                
                # Calcul du danger match
                danger_score_match = 0
                if home_shots >= 3: danger_score_match += 2
                if away_shots >= 3: danger_score_match += 2
                if home_shots >= 5: danger_score_match += 1
                if away_shots >= 5: danger_score_match += 1
                if home_corners >= 3: danger_score_match += 2
                if away_corners >= 3: danger_score_match += 2
                if home_attacks >= 8: danger_score_match += 2
                if away_attacks >= 8: danger_score_match += 2
                if home_possession > 60: danger_score_match += 1
                if away_possession > 60: danger_score_match += 1
                if minute > 75: danger_score_match += 3
                elif minute > 60: danger_score_match += 2
                
                # Buts attendus
                buts_attendus = {
                    "total": round((home_shots + away_shots) * 0.12 + (home_corners + away_corners) * 0.04 + (home_attacks + away_attacks) * 0.02, 2),
                    "1mt": round((home_shots + away_shots) * 0.05 + (home_corners + away_corners) * 0.02, 2),
                    "proba_1mt": min(95, (home_shots + away_shots) * 8)
                }
                
                all_matches.append({
                    "id": event_id,
                    "league": league_slug,
                    "home": home_team,
                    "away": away_team,
                    "home_score": home_score,
                    "away_score": away_score,
                    "minute": minute,
                    "home_shots": home_shots,
                    "away_shots": away_shots,
                    "home_corners": home_corners,
                    "away_corners": away_corners,
                    "home_possession": home_possession,
                    "away_possession": away_possession,
                    "home_attacks": home_attacks,
                    "away_attacks": away_attacks,
                    "home_shots_on_target": home_shots_on_target,
                    "away_shots_on_target": away_shots_on_target,
                    "danger_score_1mt": danger_score_1mt,
                    "danger_score_match": danger_score_match,
                    "buts_attendus": buts_attendus
                })
                
        except Exception as e:
            print(f"⚠️ Erreur ligue {league_slug}: {e}")
            continue
    
    return all_matches

print("🤖 Bot lancé - TOUTES les ligues (MODE TEST AVEC STATS SIMULÉES)")
print("📊 Les statistiques sont générées aléatoirement pour déclencher des alertes")

while True:
    try:
        matchs = get_live_matches()
        print(f"📊 {len(matchs)} matchs en direct analysés")

        alertes_envoyees = 0
        
        for match in matchs:
            match_id = match["id"]
            ancien = historique[match_id]
            minute = match["minute"]
            
            # ALERTE 1ÈRE MI-TEMPS
            if minute < 45 and match["danger_score_1mt"] >= SEUIL_DANGER_1MT:
                if ancien["last_alert_1mt"] == 0 or (time.time() - ancien["last_alert_1mt"]) > 600:
                    message = (
                        f"⚽ **ALERTE BUT - 1ÈRE MI-TEMPS** ⚽\n\n"
                        f"📍 {match['home']} {match['home_score']} - {match['away_score']} {match['away']}\n"
                        f"🏆 {match['league']}\n"
                        f"⏱️ {minute}' (1MT)\n\n"
                        f"📊 Statistiques (SIMULÉES):\n"
                        f"🔫 Tirs: {match['home_shots']} - {match['away_shots']}\n"
                        f"🎯 Tirs cadrés: {match['home_shots_on_target']} - {match['away_shots_on_target']}\n"
                        f"🏁 Corners: {match['home_corners']} - {match['away_corners']}\n"
                        f"🧊 Possession: {match['home_possession']}% - {match['away_possession']}%\n"
                        f"⚡ Attaques dangereuses: {match['home_attacks']} - {match['away_attacks']}\n\n"
                        f"📈 Prédictions:\n"
                        f"🔮 Buts attendus: {match['buts_attendus']['1mt']:.2f}\n"
                        f"🎰 Probabilité de but: {match['buts_attendus']['proba_1mt']}%\n"
                        f"⚠️ Score de danger: {match['danger_score_1mt']}/10\n\n"
                        f"🔥 Un but est très probable dans les 5 prochaines minutes !"
                    )
                    if envoyer_telegram(message):
                        alertes_envoyees += 1
                    historique[match_id]["last_alert_1mt"] = time.time()
            
            # ALERTE MATCH COMPLET
            if match["danger_score_match"] >= SEUIL_DANGER_MATCH:
                if ancien["last_alert_match"] == 0 or (time.time() - ancien["last_alert_match"]) > 600:
                    pred = match["buts_attendus"]
                    plus_0_5 = "✅" if pred["total"] > 0.5 else "❌"
                    plus_1_5 = "✅" if pred["total"] > 1.5 else "❌"
                    plus_2_5 = "✅" if pred["total"] > 2.5 else "❌"
                    plus_3_5 = "✅" if pred["total"] > 3.5 else "❌"
                    
                    message = (
                        f"⚽ **ALERTE BUT - MATCH COMPLET** ⚽\n\n"
                        f"📍 {match['home']} {match['home_score']} - {match['away_score']} {match['away']}\n"
                        f"🏆 {match['league']}\n"
                        f"⏱️ {minute}'\n\n"
                        f"📊 Statistiques (SIMULÉES):\n"
                        f"🔫 Tirs: {match['home_shots']} - {match['away_shots']}\n"
                        f"🎯 Tirs cadrés: {match['home_shots_on_target']} - {match['away_shots_on_target']}\n"
                        f"🏁 Corners: {match['home_corners']} - {match['away_corners']}\n"
                        f"🧊 Possession: {match['home_possession']}% - {match['away_possession']}%\n"
                        f"⚡ Attaques dangereuses: {match['home_attacks']} - {match['away_attacks']}\n\n"
                        f"📊 Prédictions:\n"
                        f"⚽ Plus de 0.5 but: {plus_0_5}\n"
                        f"⚽ Plus de 1.5 but: {plus_1_5}\n"
                        f"⚽ Plus de 2.5 but: {plus_2_5}\n"
                        f"⚽ Plus de 3.5 but: {plus_3_5}\n"
                        f"📈 Buts attendus: {pred['total']:.2f}\n"
                        f"🕐 Minute: {minute}'\n\n"
                        f"⚠️ Score de danger: {match['danger_score_match']}/13\n"
                        f"🔥 Un but pourrait être marqué dans les minutes qui suivent !"
                    )
                    if envoyer_telegram(message):
                        alertes_envoyees += 1
                    historique[match_id]["last_alert_match"] = time.time()
            
            # Mise à jour de l'historique
            historique[match_id]["danger_score_1mt"] = match["danger_score_1mt"]
            historique[match_id]["danger_score_match"] = match["danger_score_match"]
            historique[match_id]["home_shots"] = match["home_shots"]
            historique[match_id]["away_shots"] = match["away_shots"]
            historique[match_id]["home_corners"] = match["home_corners"]
            historique[match_id]["away_corners"] = match["away_corners"]
            historique[match_id]["home_possession"] = match["home_possession"]
            historique[match_id]["away_possession"] = match["away_possession"]
            historique[match_id]["home_attacks"] = match["home_attacks"]
            historique[match_id]["away_attacks"] = match["away_attacks"]
            historique[match_id]["home_shots_on_target"] = match["home_shots_on_target"]
            historique[match_id]["away_shots_on_target"] = match["away_shots_on_target"]

        if alertes_envoyees > 0:
            print(f"📨 {alertes_envoyees} alertes envoyées ce cycle")
        
        time.sleep(30)  # Vérification plus rapide pour les tests

    except Exception as e:
        print(f"❌ Erreur: {e}")
        time.sleep(60)
