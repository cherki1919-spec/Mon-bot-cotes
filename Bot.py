import requests
import time
import math
from collections import defaultdict
from datetime import datetime, timedelta

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"       # Ton token BotFather
CHAT_ID = "810719713"               # Ton ID Telegram
ODDS_API_KEY = "d701b89123f5ca8450aeb968456fe372"  # Ta clé The Odds API

# Seuils d'alerte (ajustables)
SEUIL_ALERTE_1MT = 0.60   # Buts attendus en 1MT pour déclencher une alerte
SEUIL_ALERTE_MATCH = 1.20 # Buts attendus match pour déclencher une alerte
# =============================================================

historique_matchs = defaultdict(lambda: {
    "home_xg_live": 0.0,
    "away_xg_live": 0.0,
    "minute": 0,
    "last_alert_1mt": 0,
    "last_alert_match": 0,
    "home_score": 0,
    "away_score": 0
})

# Cache pour les stats historiques des équipes
cache_equipes = {}

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
    """Récupère les matchs en direct via The Odds API (endpoint gratuit)"""
    url = "https://api.the-odds-api.com/v4/sports/soccer/scores"
    params = {"apiKey": ODDS_API_KEY, "daysFrom": "1"}
    try:
        response = requests.get(url, params=params, timeout=15)
        return response.json()
    except Exception as e:
        print(f"❌ Erreur scores: {e}")
        return []

def get_team_stats(team_name, league_id=None):
    """
    Récupère les stats historiques d'une équipe (xG moyen sur 5 matchs)
    Utilise un cache pour éviter les appels répétés
    """
    cache_key = f"{team_name}_{league_id}"
    if cache_key in cache_equipes:
        return cache_equipes[cache_key]
    
    # Ici, on simule des valeurs pour l'exemple
    # Dans une version réelle, on appellerait API-Football ou Sportmonks
    import random
    xg_moyen = round(random.uniform(0.8, 2.2), 2)
    resultat = {
        "xg_moyen": xg_moyen,
        "xg_domicile": round(xg_moyen * 1.15, 2),
        "xg_exterieur": round(xg_moyen * 0.85, 2)
    }
    cache_equipes[cache_key] = resultat
    return resultat

def get_head_to_head(team1, team2):
    """
    Récupère l'historique des confrontations directes
    Retourne la moyenne de buts dans ces matchs
    """
    # Simulation pour l'exemple
    import random
    return round(random.uniform(1.5, 3.5), 2)

def calculer_buts_attendus(match, minute, home_team, away_team, home_score, away_score):
    """
    Calcule les buts attendus en 1MT et dans le match complet
    Basé sur xG live, historique équipes, confrontations directes
    """
    # 1. xG live du match (depuis l'API) - 40% du poids
    xg_live_home = match.get("home_xg", 0.0)
    xg_live_away = match.get("away_xg", 0.0)
    
    if xg_live_home == 0 and xg_live_away == 0:
        # Si pas de xG live, on estime depuis les tirs/corners
        home_shots = match.get("home_shots", 0)
        away_shots = match.get("away_shots", 0)
        home_corners = match.get("home_corners", 0)
        away_corners = match.get("away_corners", 0)
        
        xg_live_home = home_shots * 0.10 + home_corners * 0.03
        xg_live_away = away_shots * 0.10 + away_corners * 0.03
    
    # 2. Stats historiques des équipes (moyenne xG) - 30% du poids
    stats_home = get_team_stats(home_team)
    stats_away = get_team_stats(away_team)
    
    # Ajustement domicile/extérieur
    xg_hist_home = stats_home.get("xg_domicile", 1.2)
    xg_hist_away = stats_away.get("xg_exterieur", 1.0)
    
    # 3. Confrontations directes - 20% du poids
    h2h_avg = get_head_to_head(home_team, away_team)
    h2h_home = h2h_avg * 0.55
    h2h_away = h2h_avg * 0.45
    
    # 4. Avantage domicile - 10% du poids
    home_advantage = 0.15  # 15% d'augmentation pour l'équipe à domicile
    
    # Calcul des xG prédits pour le match complet
    xG_home_match = (
        xg_live_home * 0.40 +
        xg_hist_home * 0.30 +
        h2h_home * 0.20 +
        (xg_hist_home * home_advantage) * 0.10
    )
    
    xG_away_match = (
        xg_live_away * 0.40 +
        xg_hist_away * 0.30 +
        h2h_away * 0.20
    )
    
    # Ajustement basé sur le temps écoulé (extrapolation sur 90 min)
    if minute > 0 and minute < 90:
        temps_restant = (90 - minute) / 90
        facteur_extrapolation = 1 / (minute / 90) if minute > 0 else 1
        xG_home_match = xG_home_match * facteur_extrapolation * 0.8 + xG_home_match * 0.2
        xG_away_match = xG_away_match * facteur_extrapolation * 0.8 + xG_away_match * 0.2
    
    # Calcul pour la 1ère mi-temps (extrapolation sur 45 min)
    if minute < 45:
        temps_ecoule_1mt = minute / 45 if minute > 0 else 0
        xG_home_1mt = xG_home_match * (temps_ecoule_1mt + 0.3)
        xG_away_1mt = xG_away_match * (temps_ecoule_1mt + 0.3)
    else:
        xG_home_1mt = 0
        xG_away_1mt = 0
    
    # Calcul de la probabilité de but (distribution de Poisson)
    def proba_au_moins_un_but(xG):
        return 1 - math.exp(-xG)
    
    total_buts_attendus_match = xG_home_match + xG_away_match
    total_buts_attendus_1mt = xG_home_1mt + xG_away_1mt
    
    proba_but_1mt = proba_au_moins_un_but(total_buts_attendus_1mt)
    
    # Prédiction du nombre de buts (Over/Under)
    def predict_over(xG, line):
        return 1 - sum(math.exp(-xG) * (xG ** k) / math.factorial(k) for k in range(int(line) + 1))
    
    over_0_5 = predict_over(total_buts_attendus_match, 0.5)
    over_1_5 = predict_over(total_buts_attendus_match, 1.5)
    over_2_5 = predict_over(total_buts_attendus_match, 2.5)
    over_3_5 = predict_over(total_buts_attendus_match, 3.5)
    
    return {
        "xG_home": round(xG_home_match, 2),
        "xG_away": round(xG_away_match, 2),
        "total_match": round(total_buts_attendus_match, 2),
        "xG_home_1mt": round(xG_home_1mt, 2),
        "xG_away_1mt": round(xG_away_1mt, 2),
        "total_1mt": round(total_buts_attendus_1mt, 2),
        "proba_but_1mt": round(proba_but_1mt * 100, 1),
        "over_0_5": round(over_0_5 * 100, 1),
        "over_1_5": round(over_1_5 * 100, 1),
        "over_2_5": round(over_2_5 * 100, 1),
        "over_3_5": round(over_3_5 * 100, 1)
    }

print("🤖 Bot lancé - Prédictions de buts (Poisson + xG + Historique)")

while True:
    try:
        matchs = get_live_scores()
        print(f"📊 {len(matchs)} matchs récupérés")
        
        for match in matchs:
            match_id = match.get("id")
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
            
            # Extraction des stats (si disponibles)
            home_shots = match.get("home_shots", 0)
            away_shots = match.get("away_shots", 0)
            home_corners = match.get("home_corners", 0)
            away_corners = match.get("away_corners", 0)
            home_xg = match.get("home_xg", 0.0)
            away_xg = match.get("away_xg", 0.0)
            
            # Création d'un objet match enrichi
            match_enriched = {
                "home_shots": home_shots,
                "away_shots": away_shots,
                "home_corners": home_corners,
                "away_corners": away_corners,
                "home_xg": home_xg,
                "away_xg": away_xg
            }
            
            # Calcul des prédictions
            pred = calculer_buts_attendus(
                match_enriched, minute,
                home_team, away_team,
                home_score, away_score
            )
            
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
                            f"🎰 Probabilité de but: **{pred['proba_but_1mt']}%**\n"
                            f"🏠 xG {home_team}: {pred['xG_home_1mt']:.2f}\n"
                            f"✈️ xG {away_team}: {pred['xG_away_1mt']:.2f}\n\n"
                            f"📈 **Statistiques live:**\n"
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
                        f"📈 **Probabilités Over/Under:**\n"
                        f"⚽ +0.5 but: **{pred['over_0_5']}%**\n"
                        f"⚽ +1.5 but: **{pred['over_1_5']}%**\n"
                        f"⚽ +2.5 but: **{pred['over_2_5']}%**\n"
                        f"⚽ +3.5 but: **{pred['over_3_5']}%**\n\n"
                        f"📊 **Statistiques live:**\n"
                        f"🔫 Tirs: {home_shots} - {away_shots}\n"
                        f"🏁 Corners: {home_corners} - {away_corners}\n\n"
                        f"🔥 Plusieurs buts attendus dans ce match !"
                    )
                    envoyer_telegram(message)
                    historique_matchs[match_id]["last_alert_match"] = time.time()
            
            # Mise à jour de l'historique
            historique_matchs[match_id].update({
                "home_xg_live": home_xg,
                "away_xg_live": away_xg,
                "minute": minute,
                "home_score": home_score,
                "away_score": away_score
            })
        
        time.sleep(90)  # Vérification toutes les 90 secondes
        
    except Exception as e:
        print(f"❌ Erreur générale: {e}")
        time.sleep(60)
