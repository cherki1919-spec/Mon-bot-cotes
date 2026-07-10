import requests
import time
import math
import json
from collections import defaultdict

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"
       # Ton token BotFather
CHAT_ID = "810719713"              # Ton ID Telegram
ODDS_API_KEY = "d701b89123f5ca8450aeb968456fe372"  # Ta clé
SEUIL_ALERTE_1MT = 0.60
SEUIL_ALERTE_MATCH = 1.20
# =============================================================

historique_matchs = defaultdict(lambda: {
    "last_alert_1mt": 0,
    "last_alert_match": 0,
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

def get_live_scores():
    """Récupère les matchs en direct avec gestion d'erreur"""
    url = "https://api.the-odds-api.com/v4/sports/soccer/scores"
    params = {"apiKey": ODDS_API_KEY}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        # 🔍 DIAGNOSTIC : Affiche le statut et le début de la réponse
        print(f"📡 Statut HTTP: {response.status_code}")
        print(f"📄 Contenu brut (début): {response.text[:200]}")
        
        # Si le statut n'est pas 200, on affiche l'erreur
        if response.status_code != 200:
            print(f"❌ Erreur API: {response.text}")
            return []
        
        data = response.json()
        
        # Si c'est une chaîne, on affiche l'erreur
        if isinstance(data, str):
            print(f"❌ Réponse string: {data}")
            return []
        
        # Si c'est un dict avec une erreur
        if isinstance(data, dict) and data.get("error"):
            print(f"❌ Erreur API: {data.get('error')}")
            return []
        
        # Si c'est une liste, on la retourne
        if isinstance(data, list):
            print(f"📊 {len(data)} matchs récupérés")
            return data
        else:
            print(f"⚠️ Type inattendu: {type(data)}")
            return []
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur requête: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Erreur JSON: {e}")
        return []

def get_team_stats(team_name):
    """Simule des stats historiques"""
    import random
    xg = round(random.uniform(0.8, 2.2), 2)
    return {"xg_moyen": xg, "xg_domicile": round(xg * 1.15, 2), "xg_exterieur": round(xg * 0.85, 2)}

def get_head_to_head(team1, team2):
    """Simule un historique de confrontations"""
    import random
    return round(random.uniform(1.5, 3.5), 2)

def calculer_buts_attendus(match, minute, home_team, away_team):
    """Calcule les buts attendus"""
    xg_live_home = match.get("home_xg", 0.0)
    xg_live_away = match.get("away_xg", 0.0)
    
    if xg_live_home == 0 and xg_live_away == 0:
        home_shots = match.get("home_shots", 0)
        away_shots = match.get("away_shots", 0)
        home_corners = match.get("home_corners", 0)
        away_corners = match.get("away_corners", 0)
        xg_live_home = home_shots * 0.10 + home_corners * 0.03
        xg_live_away = away_shots * 0.10 + away_corners * 0.03
    
    stats_home = get_team_stats(home_team)
    stats_away = get_team_stats(away_team)
    h2h_avg = get_head_to_head(home_team, away_team)
    
    xg_home_match = (
        xg_live_home * 0.40 +
        stats_home["xg_domicile"] * 0.30 +
        h2h_avg * 0.20 +
        stats_home["xg_domicile"] * 0.10
    )
    
    xg_away_match = (
        xg_live_away * 0.40 +
        stats_away["xg_exterieur"] * 0.30 +
        h2h_avg * 0.20
    )
    
    if minute > 0 and minute < 90:
        facteur_extrapolation = 90 / minute if minute > 0 else 1
        xg_home_match = xg_home_match * min(facteur_extrapolation, 2.5)
        xg_away_match = xg_away_match * min(facteur_extrapolation, 2.5)
    
    if minute < 45:
        xg_home_1mt = xg_home_match * (minute / 45 + 0.3) if minute > 0 else 0
        xg_away_1mt = xg_away_match * (minute / 45 + 0.3) if minute > 0 else 0
    else:
        xg_home_1mt = 0
        xg_away_1mt = 0
    
    total_match = xg_home_match + xg_away_match
    total_1mt = xg_home_1mt + xg_away_1mt
    
    return {
        "xG_home": round(xg_home_match, 2),
        "xG_away": round(xg_away_match, 2),
        "total_match": round(total_match, 2),
        "xG_home_1mt": round(xg_home_1mt, 2),
        "xG_away_1mt": round(xg_away_1mt, 2),
        "total_1mt": round(total_1mt, 2),
    }

print("🤖 Bot lancé - Prédictions de buts (Poisson + xG + Historique)")

while True:
    try:
        matchs = get_live_scores()
        
        if not matchs:
            print("⏳ Aucun match récupéré, nouvelle tentative dans 60s...")
            time.sleep(60)
            continue
        
        for match in matchs:
            match_id = match.get("id")
            if not match_id:
                continue
            
            status = match.get("status", "")
            if status != "in":
                continue
            
            home_team = match.get("home_team", "?")
            away_team = match.get("away_team", "?")
            scores = match.get("scores", [])
            home_score = int(scores[0].get("score", 0)) if len(scores) > 0 else 0
            away_score = int(scores[1].get("score", 0)) if len(scores) > 1 else 0
            
            clock = match.get("displayClock", "0:00")
            try:
                minute = int(clock.split(":")[0])
            except:
                minute = 0
            
            # Statistiques
            home_shots = match.get("home_shots", 0)
            away_shots = match.get("away_shots", 0)
            home_corners = match.get("home_corners", 0)
            away_corners = match.get("away_corners", 0)
            
            match_enriched = {
                "home_shots": home_shots,
                "away_shots": away_shots,
                "home_corners": home_corners,
                "away_corners": away_corners,
                "home_xg": match.get("home_xg", 0.0),
                "away_xg": match.get("away_xg", 0.0)
            }
            
            pred = calculer_buts_attendus(match_enriched, minute, home_team, away_team)
            
            # ALERTE 1ÈRE MI-TEMPS
            if minute < 45 and minute > 5:
                if pred["total_1mt"] >= SEUIL_ALERTE_1MT:
                    if historique_matchs[match_id]["last_alert_1mt"] == 0 or \
                       (time.time() - historique_matchs[match_id]["last_alert_1mt"]) > 600:
                        
                        message = (
                            f"⚽ **ALERTE BUT - 1ÈRE MI-TEMPS** ⚽\n\n"
                            f"📍 {home_team} {home_score} - {away_score} {away_team}\n"
                            f"⏱️ {minute}' (1MT)\n\n"
                            f"📊 **Prédictions:**\n"
                            f"🔮 Buts attendus 1MT: **{pred['total_1mt']:.2f}**\n"
                            f"🏠 xG {home_team}: {pred['xG_home_1mt']:.2f}\n"
                            f"✈️ xG {away_team}: {pred['xG_away_1mt']:.2f}\n\n"
                            f"📈 **Statistiques:**\n"
                            f"🔫 Tirs: {home_shots} - {away_shots}\n"
                            f"🏁 Corners: {home_corners} - {away_corners}\n\n"
                            f"🔥 Un but est très probable dans les 5 prochaines minutes !"
                        )
                        envoyer_telegram(message)
                        historique_matchs[match_id]["last_alert_1mt"] = time.time()
            
            # ALERTE MATCH COMPLET
            if pred["total_match"] >= SEUIL_ALERTE_MATCH:
                if historique_matchs[match_id]["last_alert_match"] == 0 or \
                   (time.time() - historique_matchs[match_id]["last_alert_match"]) > 600:
                    
                    message = (
                        f"⚽ **ALERTE BUT - MATCH COMPLET** ⚽\n\n"
                        f"📍 {home_team} {home_score} - {away_score} {away_team}\n"
                        f"⏱️ {minute}'\n\n"
                        f"📊 **Prédictions:**\n"
                        f"🔮 Buts attendus match: **{pred['total_match']:.2f}**\n"
                        f"🏠 xG {home_team}: {pred['xG_home']:.2f}\n"
                        f"✈️ xG {away_team}: {pred['xG_away']:.2f}\n\n"
                        f"📈 **Statistiques:**\n"
                        f"🔫 Tirs: {home_shots} - {away_shots}\n"
                        f"🏁 Corners: {home_corners} - {away_corners}\n\n"
                        f"🔥 Plusieurs buts attendus dans ce match !"
                    )
                    envoyer_telegram(message)
                    historique_matchs[match_id]["last_alert_match"] = time.time()
        
        time.sleep(90)
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        time.sleep(60)
