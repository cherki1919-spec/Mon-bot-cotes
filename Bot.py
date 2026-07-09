import requests
import time
from collections import defaultdict
from datetime import datetime

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"  # Remplace par ton token BotFather
CHAT_ID = "810719713"       # Remplace par ton ID Telegram
SEUIL_DANGER = 5              # Score de dangerosité pour alerter
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
    except Exception as e:
        print(f"❌ Erreur envoi: {e}")

def get_live_matches_espn():
    """Récupère les matchs en direct depuis ESPN"""
    try:
        url = "https://site.api.espn.com/apis/site/v2/sports/soccer/scoreboard"
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if "events" in data and len(data["events"]) > 0:
            matchs = []
            for event in data["events"]:
                home_team = event["competitions"][0]["competitors"][0]["team"]["displayName"]
                away_team = event["competitions"][0]["competitors"][1]["team"]["displayName"]
                home_score = int(event["competitions"][0]["competitors"][0]["score"])
                away_score = int(event["competitions"][0]["competitors"][1]["score"])
                
                # Minute du match
                minute = 0
                if "status" in event:
                    if event["status"]["type"]["name"] == "in":
                        clock = event["status"].get("displayClock", "0:00")
                        if ":" in clock:
                            minute = int(clock.split(":")[0])
                
                # Statistiques
                home_shots = 0
                away_shots = 0
                home_corners = 0
                away_corners = 0
                home_possession = 50
                away_possession = 50
                home_attacks = 0
                away_attacks = 0
                home_shots_on_target = 0
                away_shots_on_target = 0
                
                if "statistics" in event["competitions"][0]:
                    for stat in event["competitions"][0]["statistics"]:
                        if stat.get("name") == "shots":
                            for team_stat in stat.get("values", []):
                                if team_stat.get("teamId") == event["competitions"][0]["competitors"][0]["team"]["id"]:
                                    home_shots = int(team_stat.get("value", 0))
                                else:
                                    away_shots = int(team_stat.get("value", 0))
                        elif stat.get("name") == "cornerKicks":
                            for team_stat in stat.get("values", []):
                                if team_stat.get("teamId") == event["competitions"][0]["competitors"][0]["team"]["id"]:
                                    home_corners = int(team_stat.get("value", 0))
                                else:
                                    away_corners = int(team_stat.get("value", 0))
                        elif stat.get("name") == "possession":
                            for team_stat in stat.get("values", []):
                                if team_stat.get("teamId") == event["competitions"][0]["competitors"][0]["team"]["id"]:
                                    home_possession = int(team_stat.get("value", 50))
                                else:
                                    away_possession = int(team_stat.get("value", 50))
                        elif stat.get("name") == "dangerousAttacks":
                            for team_stat in stat.get("values", []):
                                if team_stat.get("teamId") == event["competitions"][0]["competitors"][0]["team"]["id"]:
                                    home_attacks = int(team_stat.get("value", 0))
                                else:
                                    away_attacks = int(team_stat.get("value", 0))
                        elif stat.get("name") == "shotsOnTarget":
                            for team_stat in stat.get("values", []):
                                if team_stat.get("teamId") == event["competitions"][0]["competitors"][0]["team"]["id"]:
                                    home_shots_on_target = int(team_stat.get("value", 0))
                                else:
                                    away_shots_on_target = int(team_stat.get("value", 0))
                
                # Calcul du danger 1MT
                danger_score_1mt = 0
                if minute < 45:
                    if home_shots >= 3: danger_score_1mt += 2
                    if away_shots >= 3: danger_score_1mt += 2
                    if home_corners >= 2: danger_score_1mt += 1
                    if away_corners >= 2: danger_score_1mt += 1
                    if home_attacks >= 5: danger_score_1mt += 2
                    if away_attacks >= 5: danger_score_1mt += 2
                    if home_possession > 60: danger_score_1mt += 1
                    if away_possession > 60: danger_score_1mt += 1
                
                # Calcul du danger match
                danger_score_match = 0
                if home_shots >= 5: danger_score_match += 2
                if away_shots >= 5: danger_score_match += 2
                if home_shots >= 8: danger_score_match += 1
                if away_shots >= 8: danger_score_match += 1
                if home_corners >= 3: danger_score_match += 2
                if away_corners >= 3: danger_score_match += 2
                if home_attacks >= 10: danger_score_match += 2
                if away_attacks >= 10: danger_score_match += 2
                if home_possession > 60: danger_score_match += 1
                if away_possession > 60: danger_score_match += 1
                if minute > 75: danger_score_match += 3
                elif minute > 60: danger_score_match += 2
                
                # Calcul des buts attendus
                buts_attendus = {
                    "total": round((home_shots + away_shots) * 0.12 + (home_corners + away_corners) * 0.04 + (home_attacks + away_attacks) * 0.02, 2),
                    "1mt": round((home_shots + away_shots) * 0.05 + (home_corners + away_corners) * 0.02, 2),
                    "proba_1mt": min(95, (home_shots + away_shots) * 8)
                }
                
                matchs.append({
                    "id": event["id"],
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
            return matchs
        else:
            # Aucun match réel, on simule un match de test
            print("📭 Aucun match en direct, utilisation d'un match de test")
            return [{
                "id": "test_1",
                "home": "Équipe Test A",
                "away": "Équipe Test B",
                "home_score": 0,
                "away_score": 0,
                "minute": 35,
                "home_shots": 6,
                "away_shots": 3,
                "home_corners": 4,
                "away_corners": 1,
                "home_possession": 65,
                "away_possession": 35,
                "home_attacks": 8,
                "away_attacks": 3,
                "home_shots_on_target": 3,
                "away_shots_on_target": 1,
                "danger_score_1mt": 5,
                "danger_score_match": 7,
                "buts_attendus": {
                    "total": 1.25,
                    "1mt": 0.75,
                    "proba_1mt": 72
                }
            }]
    except Exception as e:
        print(f"❌ Erreur: {e}")
        # En cas d'erreur, on renvoie un match de test
        return [{
            "id": "test_2",
            "home": "Test Home",
            "away": "Test Away",
            "home_score": 0,
            "away_score": 0,
            "minute": 40,
            "home_shots": 7,
            "away_shots": 2,
            "home_corners": 5,
            "away_corners": 1,
            "home_possession": 70,
            "away_possession": 30,
            "home_attacks": 10,
            "away_attacks": 2,
            "home_shots_on_target": 4,
            "away_shots_on_target": 1,
            "danger_score_1mt": 6,
            "danger_score_match": 8,
            "buts_attendus": {
                "total": 1.50,
                "1mt": 0.90,
                "proba_1mt": 80
            }
        }]

print("🤖 Bot lancé - Analyse des matchs en direct (prédictions de buts)")

while True:
    try:
        matchs = get_live_matches_espn()
        print(f"📊 {len(matchs)} matchs en direct analysés")

        for match in matchs:
            match_id = match["id"]
            ancien = historique[match_id]
            minute = match["minute"]
            
            # ALERTE 1ÈRE MI-TEMPS
            if minute < 45 and match["danger_score_1mt"] >= 4:
                if ancien["last_alert_1mt"] == 0 or (time.time() - ancien["last_alert_1mt"]) > 600:
                    message = (
                        f"⚽ **ALERTE BUT - 1ÈRE MI-TEMPS** ⚽\n\n"
                        f"📍 {match['home']} {match['home_score']} - {match['away_score']} {match['away']}\n"
                        f"⏱️ {minute}' (1MT)\n\n"
                        f"📊 Statistiques (1MT):\n"
                        f"🔫 Tirs: {match['home_shots']} - {match['away_shots']}\n"
                        f"🎯 Tirs cadrés: {match['home_shots_on_target']} - {match['away_shots_on_target']}\n"
                        f"🏁 Corners: {match['home_corners']} - {match['away_corners']}\n"
                        f"🧊 Possession: {match['home_possession']}% - {match['away_possession']}%\n"
                        f"⚡ Attaques dangereuses: {match['home_attacks']} - {match['away_attacks']}\n\n"
                        f"📈 Prédictions 1MT:\n"
                        f"🔮 Buts attendus: {match['buts_attendus']['1mt']:.2f}\n"
                        f"🎰 Probabilité de but: {match['buts_attendus']['proba_1mt']}%\n"
                        f"⚠️ Score de danger: {match['danger_score_1mt']}/8\n\n"
                        f"🔥 Un but est très probable dans les 5 prochaines minutes !"
                    )
                    envoyer_telegram(message)
                    historique[match_id]["last_alert_1mt"] = time.time()
            
            # ALERTE MATCH COMPLET
            if match["danger_score_match"] >= 5:
                if ancien["last_alert_match"] == 0 or (time.time() - ancien["last_alert_match"]) > 600:
                    pred = match["buts_attendus"]
                    # Détermination des prédictions
                    plus_0_5 = "✅" if pred["total"] > 0.5 else "❌"
                    plus_1_5 = "✅" if pred["total"] > 1.5 else "❌"
                    plus_2_5 = "✅" if pred["total"] > 2.5 else "❌"
                    plus_3_5 = "✅" if pred["total"] > 3.5 else "❌"
                    
                    message = (
                        f"⚽ **ALERTE BUT - MATCH COMPLET** ⚽\n\n"
                        f"📍 {match['home']} {match['home_score']} - {match['away_score']} {match['away']}\n"
                        f"⏱️ {minute}'\n\n"
                        f"📊 **Statistiques live:**\n"
                        f"🔫 Tirs: {match['home_shots']} - {match['away_shots']}\n"
                        f"🎯 Tirs cadrés: {match['home_shots_on_target']} - {match['away_shots_on_target']}\n"
                        f"🏁 Corners: {match['home_corners']} - {match['away_corners']}\n"
                        f"🧊 Possession: {match['home_possession']}% - {match['away_possession']}%\n"
                        f"⚡ Attaques dangereuses: {match['home_attacks']} - {match['away_attacks']}\n\n"
                        f"📊 **Prédictions de buts:**\n"
                        f"⚽ Plus de 0.5 but: {plus_0_5}\n"
                        f"⚽ Plus de 1.5 but: {plus_1_5}\n"
                        f"⚽ Plus de 2.5 but: {plus_2_5}\n"
                        f"⚽ Plus de 3.5 but: {plus_3_5}\n"
                        f"📈 Buts attendus: {pred['total']:.2f}\n"
                        f"🕐 Minute: {minute}'\n\n"
                        f"⚠️ Score de danger: {match['danger_score_match']}/11\n"
                        f"🔥 Un but pourrait être marqué dans les minutes qui suivent !"
                    )
                    envoyer_telegram(message)
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

        time.sleep(60)

    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        time.sleep(60)
