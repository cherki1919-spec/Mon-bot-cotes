import requests
import time
from collections import defaultdict
from datetime import datetime

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"  # Remplace par ton token BotFather
CHAT_ID = "810719713"       # Remplace par ton ID Telegram
SEUIL_DANGER_1MT = 4          # Seuil pour alerte 1ère MT
SEUIL_DANGER_MATCH = 5        # Seuil pour alerte match complet

# ==== LISTE DE TOUTES LES LIGUES (à partir de la documentation ESPN) ====
# Cette liste est une compilation des slugs pour le football masculin,
# féminin, les jeunes, les compétitions internationales, etc.
# Source: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/soccer.md
LEAGUE_SLUGS = [
    # --- International / FIFA ---
    "fifa.world", "fifa.wwc", "fifa.world.u20", "fifa.world.u17",
    "fifa.wworld.u17", "fifa.friendly", "fifa.friendly.w", "fifa.friendly_u21",
    "fifa.u20.friendly", "fifa.olympics", "fifa.w.olympics",
    "fifa.worldq", "fifa.worldq.uefa", "fifa.worldq.caf", "fifa.worldq.afc",
    "fifa.worldq.concacaf", "fifa.worldq.conmebol", "fifa.worldq.ofc",

    # --- UEFA ---
    "uefa.champions", "uefa.champions_qual", "uefa.europa", "uefa.europa_qual",
    "uefa.europa.conf", "uefa.europa.conf_qual", "uefa.super_cup",
    "uefa.wchampions", "uefa.euro", "uefa.euroq", "uefa.weuro",
    "uefa.euro_u21", "uefa.euro_u21_qual", "uefa.euro.u19", "uefa.nations",
    "uefa.w.nations",

    # --- Europe (Top divisions & divisions inférieures) ---
    "eng.1", "eng.2", "eng.3", "eng.4",
    "esp.1", "esp.2",
    "ger.1", "ger.2",
    "ita.1", "ita.2",
    "fra.1", "fra.2",
    "ned.1", "ned.2",
    "por.1",
    "bel.1",
    "sco.1", "sco.2",
    "aut.1",
    "gre.1",
    "tur.1",
    "den.1",
    "nor.1",
    "swe.1",
    "cyp.1",
    "irl.1",
    "rus.1",

    # --- Amériques ---
    "usa.1", "usa.nwsl",
    "mex.1", "mex.2",
    "conmebol.libertadores", "conmebol.sudamericana", "conmebol.recopa",
    "conmebol.america", "conmebol.america.femenina",
    "arg.1",
    "bra.1", "bra.2",
    "chi.1",
    "col.1",
    "par.1",
    "per.1",
    "uru.1",
    "bol.1",
    "ecu.1",
    "ven.1",

    # --- Afrique ---
    "caf.nations", "caf.nations_qual",
    "caf.champions", "caf.confed",
    "rsa.1",
    "nga.1",
    "gha.1",
    "alg.1", # Algérie
    "cmr.1", # Cameroun
    "tun.1", # Tunisie

    # --- Asie / Océanie ---
    "afc.champions", "afc.cup", "afc.asian.cup",
    "ksa.1",
    "jpn.1",
    "chn.1",
    "ind.1",
    "tha.1",
    "mys.1",
    "idn.1",
    "sgp.1",
    "aus.1",

    # --- Compétitions féminines ---
    "eng.w.1",
    "esp.w.1",
    "fra.w.1",
    "ned.w.1",
    "aus.w.1",
    "usa.nwsl",

    # --- Amicales et autres ---
    "club.friendly",
    "concacaf.gold",
    "concacaf.w.gold",
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
    except Exception as e:
        print(f"❌ Erreur envoi: {e}")

def get_live_matches():
    """Récupère les matchs en direct pour TOUTES les ligues de la liste."""
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
                
                # Équipes et scores
                home_team = competitors[0].get("team", {}).get("displayName", "?")
                away_team = competitors[1].get("team", {}).get("displayName", "?")
                home_score = int(competitors[0].get("score", 0))
                away_score = int(competitors[1].get("score", 0))
                
                # Minute du match
                minute = 0
                status = event.get("status", {})
                if status.get("type", {}).get("name") == "in":
                    clock = status.get("displayClock", "0:00")
                    if ":" in clock:
                        try:
                            minute = int(clock.split(":")[0])
                        except ValueError:
                            minute = 0
                
                # Statistiques (simplifiées pour l'exemple)
                # Note: ESPN ne renvoie pas toujours les statistiques détaillées sur ce endpoint
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
                
                # Buts attendus
                buts_attendus = {
                    "total": round((home_shots + away_shots) * 0.12 + (home_corners + away_corners) * 0.04, 2),
                    "1mt": round((home_shots + away_shots) * 0.05 + (home_corners + away_corners) * 0.02, 2),
                    "proba_1mt": min(95, (home_shots + away_shots) * 8)
                }
                
                all_matches.append({
                    "id": event.get("id"),
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
            print(f"⚠️ Erreur pour la ligue {league_slug}: {e}")
            continue
    
    return all_matches

print("🤖 Bot lancé - Analyse de TOUTES les ligues (via ESPN)")

while True:
    try:
        matchs = get_live_matches()
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
                        f"🏆 Ligue: {match['league']}\n"
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
                        f"🏆 Ligue: {match['league']}\n"
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
