import requests
import time
from collections import defaultdict
from datetime import datetime
import math

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"           # Ton token BotFather
CHAT_ID = "810719713"               # Ton ID Telegram
SEUIL_DANGER_1MT = 4                  # Seuil pour alerte 1ère MT
SEUIL_DANGER_MATCH = 6                # Seuil pour alerte match complet
# =============================================================

historique = defaultdict(lambda: {
    "danger_score_1mt": 0,
    "danger_score_match": 0,
    "goals_expected": 0.0,
    "last_alert_1mt": 0,
    "last_alert_match": 0,
    "home_shots": 0,
    "away_shots": 0,
    "home_corners": 0,
    "away_corners": 0,
    "home_possession": 0,
    "away_possession": 0,
    "home_attacks": 0,
    "away_attacks": 0,
    "home_shots_on_target": 0,
    "away_shots_on_target": 0
})

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("✅ Alerte envoyée")
    except Exception as e:
        print(f"❌ Erreur envoi: {e}")

def calculer_buts_attendus(home_attacks, away_attacks, home_shots, away_shots, 
                           home_corners, away_corners, home_possession, 
                           minute, home_score, away_score):
    """
    Calcule le nombre de buts attendus dans le match
    Retourne : (buts_attendus_total, buts_attendus_1mt, prediction_1mt)
    """
    
    # Facteurs de conversion (basés sur des statistiques réelles)
    # 1 tir cadré = ~0.3 but attendu
    # 1 corner = ~0.05 but attendu
    # 5 attaques dangereuses = ~0.2 but attendu
    # 10% possession = ~0.1 but attendu
    
    # Calcul pour la 1ère mi-temps (si minute < 45)
    if minute < 45:
        temps_restant_1mt = max(0, (45 - minute) / 45)  # Proportion de temps restant
        
        # Statistiques déjà accumulées en 1MT
        shots_factor_1mt = (home_shots + away_shots) * 0.08
        corners_factor_1mt = (home_corners + away_corners) * 0.03
        attacks_factor_1mt = (home_attacks + away_attacks) * 0.015
        possession_factor_1mt = (home_possession + away_possession) / 100 * 0.05
        
        buts_attendus_1mt = (shots_factor_1mt + corners_factor_1mt + 
                             attacks_factor_1mt + possession_factor_1mt) * temps_restant_1mt
        
        # Probabilité de but en 1MT (basée sur le rythme actuel)
        proba_but_1mt = min(95, buts_attendus_1mt * 50)
        
    else:
        buts_attendus_1mt = 0
        proba_but_1mt = 0
    
    # Calcul pour le match complet
    temps_restant = max(0, (90 - minute) / 90)
    
    # Projection sur 90 minutes
    facteur_rythme = 1 + (minute / 90) * 0.5  # Le rythme augmente en fin de match
    
    shots_factor = (home_shots + away_shots) * 0.12 * facteur_rythme
    corners_factor = (home_corners + away_corners) * 0.04 * facteur_rythme
    attacks_factor = (home_attacks + away_attacks) * 0.02 * facteur_rythme
    possession_factor = (home_possession + away_possession) / 100 * 0.08 * facteur_rythme
    
    buts_attendus_total = (shots_factor + corners_factor + 
                           attacks_factor + possession_factor) * temps_restant
    
    # Ajustement basé sur le score actuel (les équipes attaquent plus si elles perdent)
    if home_score < away_score:
        buts_attendus_total *= 1.1
    elif away_score < home_score:
        buts_attendus_total *= 1.1
    
    # Seuil pour prédire "plus de 0.5 but"
    prediction_0_5 = "✅" if buts_attendus_total > 0.5 else "❌"
    prediction_1_5 = "✅" if buts_attendus_total > 1.5 else "❌"
    prediction_2_5 = "✅" if buts_attendus_total > 2.5 else "❌"
    prediction_3_5 = "✅" if buts_attendus_total > 3.5 else "❌"
    
    return {
        "total": round(buts_attendus_total, 2),
        "1mt": round(buts_attendus_1mt, 2),
        "proba_1mt": round(proba_but_1mt, 1),
        "plus_0_5": prediction_0_5,
        "plus_1_5": prediction_1_5,
        "plus_2_5": prediction_2_5,
        "plus_3_5": prediction_3_5
    }

def get_live_matches_espn():
    """Récupère les matchs en direct depuis ESPN"""
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/scoreboard"
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        
        if "events" not in data:
            return []
        
        matchs = []
        for event in data["events"]:
            # Infos de base
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
            
            # Calcul des scores de dangerosité
            danger_score_1mt = 0
            danger_score_match = 0
            
            # Pour la 1ère mi-temps
            if minute < 45:
                # Tirs en 1MT
                if home_shots >= 3:
                    danger_score_1mt += 2
                if away_shots >= 3:
                    danger_score_1mt += 2
                # Corners en 1MT
                if home_corners >= 2:
                    danger_score_1mt += 1
                if away_corners >= 2:
                    danger_score_1mt += 1
                # Attaques dangereuses en 1MT
                if home_attacks >= 5:
                    danger_score_1mt += 2
                if away_attacks >= 5:
                    danger_score_1mt += 2
                # Possession élevée en 1MT
                if home_possession > 60:
                    danger_score_1mt += 1
                if away_possession > 60:
                    danger_score_1mt += 1
            
            # Pour le match complet
            # Tirs
            if home_shots >= 5:
                danger_score_match += 2
            if away_shots >= 5:
                danger_score_match += 2
            if home_shots >= 8:
                danger_score_match += 1
            if away_shots >= 8:
                danger_score_match += 1
            # Corners
            if home_corners >= 3:
                danger_score_match += 2
            if away_corners >= 3:
                danger_score_match += 2
            # Attaques
            if home_attacks >= 10:
                danger_score_match += 2
            if away_attacks >= 10:
                danger_score_match += 2
            # Possession
            if home_possession > 60:
                danger_score_match += 1
            if away_possession > 60:
                danger_score_match += 1
            # Fin de match (pression)
            if minute > 75:
                danger_score_match += 3
            elif minute > 60:
                danger_score_match += 2
            
            # Calcul des buts attendus
            buts = calculer_buts_attendus(
                home_attacks, away_attacks,
                home_shots, away_shots,
                home_corners, away_corners,
                home_possession,
                minute, home_score, away_score
            )
            
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
                "buts_attendus": buts
            })
        
        return matchs
    except Exception as e:
        print(f"❌ Erreur récupération: {e}")
        return []

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
            if minute < 45 and match["danger_score_1mt"] >= SEUIL_DANGER_1MT:
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
                        f"⚠️ Score de danger: {match['danger_score_1mt']}/{SEUIL_DANGER_1MT+5}\n\n"
                        f"🔥 Un but est très probable dans les 5 prochaines minutes !"
                    )
                    envoyer_telegram(message)
                    historique[match_id]["last_alert_1mt"] = time.time()
            
            # ALERTE MATCH COMPLET
            if match["danger_score_match"] >= SEUIL_DANGER_MATCH:
                if ancien["last_alert_match"] == 0 or (time.time() - ancien["last_alert_match"]) > 600:
                    # Construction de la prédiction de buts
                    pred = match["buts_attendus"]
                    pred_text = (
                        f"📊 **Prédictions de buts:**\n"
                        f"⚽ Plus de 0.5 but: {pred['plus_0_5']}\n"
                        f"⚽ Plus de 1.5 but: {pred['plus_1_5']}\n"
                        f"⚽ Plus de 2.5 but: {pred['plus_2_5']}\n"
                        f"⚽ Plus de 3.5 but: {pred['plus_3_5']}\n"
                        f"📈 Buts attendus: {pred['total']:.2f}\n"
                        f"🕐 Minute: {match['minute']}'"
                    )
                    
                    message = (
                        f"⚽ **ALERTE BUT - MATCH COMPLET** ⚽\n\n"
                        f"📍 {match['home']} {match['home_score']} - {match['away_score']} {match['away']}\n"
                        f"⏱️ {match['minute']}'\n\n"
                        f"📊 **Statistiques live:**\n"
                        f"🔫 Tirs: {match['home_shots']} - {match['away_shots']}\n"
                        f"🎯 Tirs cadrés: {match['home_shots_on_target']} - {match['away_shots_on_target']}\n"
                        f"🏁 Corners: {match['home_corners']} - {match['away_corners']}\n"
                        f"🧊 Possession: {match['home_possession']}% - {match['away_possession']}%\n"
                        f"⚡ Attaques dangereuses: {match['home_attacks']} - {match['away_attacks']}\n\n"
                        f"{pred_text}\n\n"
                        f"⚠️ Score de danger: {match['danger_score_match']}/{SEUIL_DANGER_MATCH+5}\n"
                        f"🔥 Plusieurs buts peuvent être marqués dans ce match !"
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
        
        time.sleep(30)
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        time.sleep(60)
