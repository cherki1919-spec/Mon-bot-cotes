import requests
import time
import re
import json
from collections import defaultdict
from datetime import datetime

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"
  # Remplace par ton token BotFather
CHAT_ID = "810719713"       # Remplace par ton ID Telegram
SEUIL_DANGER_1MT = 2          # Seuil pour alerte 1ère MT
SEUIL_DANGER_MATCH = 2        # Seuil pour alerte match complet
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

def get_live_matches_flashscore():
    """Récupère les matchs en direct avec stats depuis Flashscore"""
    all_matches = []
    
    # Flashscore utilise une API interne
    url = "https://d.flashscore.com/x/feed/f_1_1_2_en_1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Origin": "https://www.flashscore.com",
        "Referer": "https://www.flashscore.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        data = response.text
        
        # Extraction des matchs en direct
        # Format: "ID~ÉquipeA~ÉquipeB~ScoreA~ScoreB~Minute~..."
        pattern = r'(\d+)~([^~]+)~([^~]+)~(\d+)~(\d+)~([^~]+)~'
        matches = re.findall(pattern, data)
        
        for match in matches:
            try:
                match_id = match[0]
                home = match[1].strip()
                away = match[2].strip()
                home_score = int(match[3])
                away_score = int(match[4])
                minute_str = match[5]
                
                # Extraction de la minute
                minute = 0
                if "'" in minute_str:
                    try:
                        minute = int(minute_str.replace("'", ""))
                    except:
                        minute = 0
                
                # Recherche des statistiques
                stat_pattern = rf'{match_id}~.*?"statistics":\[(.*?)\]'
                stat_match = re.search(stat_pattern, data)
                
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
                
                if stat_match:
                    stats_str = stat_match.group(1)
                    # Extraction des valeurs
                    # Format: "stat_name","home_value","away_value"
                    stat_items = re.findall(r'"([^"]+)","([^"]+)","([^"]+)"', stats_str)
                    for stat_name, home_val, away_val in stat_items:
                        if "shots" in stat_name.lower():
                            try:
                                home_shots = int(home_val) if home_val.isdigit() else 0
                                away_shots = int(away_val) if away_val.isdigit() else 0
                            except:
                                pass
                        elif "corners" in stat_name.lower() or "corner" in stat_name.lower():
                            try:
                                home_corners = int(home_val) if home_val.isdigit() else 0
                                away_corners = int(away_val) if away_val.isdigit() else 0
                            except:
                                pass
                        elif "possession" in stat_name.lower():
                            try:
                                home_possession = int(home_val.replace("%", "")) if home_val else 50
                                away_possession = int(away_val.replace("%", "")) if away_val else 50
                            except:
                                pass
                        elif "attacks" in stat_name.lower():
                            try:
                                home_attacks = int(home_val) if home_val.isdigit() else 0
                                away_attacks = int(away_val) if away_val.isdigit() else 0
                            except:
                                pass
                        elif "shots on target" in stat_name.lower():
                            try:
                                home_shots_on_target = int(home_val) if home_val.isdigit() else 0
                                away_shots_on_target = int(away_val) if away_val.isdigit() else 0
                            except:
                                pass
                
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
                    "id": match_id,
                    "league": "Flashscore",
                    "home": home,
                    "away": away,
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
                print(f"⚠️ Erreur match: {e}")
                continue
        
        return all_matches
    except Exception as e:
        print(f"❌ Erreur scraping: {e}")
        return []

print("🤖 Bot lancé - Scraping Flashscore (stats réelles)")

while True:
    try:
        matchs = get_live_matches_flashscore()
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
                        f"🏆 Flashscore\n"
                        f"⏱️ {minute}' (1MT)\n\n"
                        f"📊 **Statistiques live:**\n"
                        f"🔫 Tirs: {match['home_shots']} - {match['away_shots']}\n"
                        f"🎯 Tirs cadrés: {match['home_shots_on_target']} - {match['away_shots_on_target']}\n"
                        f"🏁 Corners: {match['home_corners']} - {match['away_corners']}\n"
                        f"🧊 Possession: {match['home_possession']}% - {match['away_possession']}%\n"
                        f"⚡ Attaques dangereuses: {match['home_attacks']} - {match['away_attacks']}\n\n"
                        f"📈 **Prédictions:**\n"
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
                        f"🏆 Flashscore\n"
                        f"⏱️ {minute}'\n\n"
                        f"📊 **Statistiques live:**\n"
                        f"🔫 Tirs: {match['home_shots']} - {match['away_shots']}\n"
                        f"🎯 Tirs cadrés: {match['home_shots_on_target']} - {match['away_shots_on_target']}\n"
                        f"🏁 Corners: {match['home_corners']} - {match['away_corners']}\n"
                        f"🧊 Possession: {match['home_possession']}% - {match['away_possession']}%\n"
                        f"⚡ Attaques dangereuses: {match['home_attacks']} - {match['away_attacks']}\n\n"
                        f"📊 **Prédictions:**\n"
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
            print(f"📨 {alertes_envoyees} alertes envoyées")
        
        time.sleep(60)

    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        time.sleep(60)
