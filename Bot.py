import requests
import time
from collections import defaultdict
from datetime import datetime

# ======================= CONFIGURATION =======================
TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"  # Remplace par ton token BotFather
CHAT_ID = "810719713"       # Remplace par ton ID Telegram
SEUIL_DANGER_1MT = 2          # Seuil pour alerte 1ère MT
SEUIL_DANGER_MATCH = 2        # Seuil pour alerte match complet

# ==== TOUTES LES LIGUES ====
LEAGUE_SLUGS = [
    # --- International ---
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

    # --- Europe (Top divisions) ---
    "eng.1", "eng.2", "eng.3", "eng.4",
    "esp.1", "esp.2", "esp.3",
    "ger.1", "ger.2", "ger.3",
    "ita.1", "ita.2", "ita.3",
    "fra.1", "fra.2", "fra.3",
    "ned.1", "ned.2",
    "por.1", "por.2",
    "bel.1", "bel.2",
    "sco.1", "sco.2",
    "aut.1", "aut.2",
    "gre.1", "gre.2",
    "tur.1", "tur.2",
    "den.1", "den.2",
    "nor.1", "nor.2",
    "swe.1", "swe.2",
    "cyp.1",
    "irl.1",
    "rus.1",
    "czech.1",
    "pol.1",
    "ukr.1",
    "croatia.1",
    "serbia.1",
    "romania.1",
    "switzerland.1",
    "bulgaria.1",
    "slovakia.1",
    "slovenia.1",
    "hungary.1",
    "israel.1",
    "kazakhstan.1",
    "kosovo.1",
    "albania.1",
    "north.macedonia.1",
    "montenegro.1",
    "malta.1",

    # --- Europe (Ligues jeunes) ---
    "uefa.youth.league",
    "eng.u21", "eng.u18",
    "esp.u19",
    "ger.u19", "ger.u17",

    # --- Amérique du Nord ---
    "usa.1", "usa.2",
    "usa.nwsl",
    "mex.1", "mex.2",
    "mex.liga.mx.femenil",
    "concacaf.champions",
    "concacaf.gold",
    "concacaf.w.gold",

    # --- Amérique du Sud ---
    "conmebol.libertadores", "conmebol.sudamericana", "conmebol.recopa",
    "conmebol.america", "conmebol.america.femenina",
    "arg.1", "arg.2",
    "bra.1", "bra.2", "bra.3",
    "chi.1", "chi.2",
    "col.1", "col.2",
    "par.1", "par.2",
    "per.1",
    "uru.1",
    "bol.1",
    "ecu.1",
    "ven.1",

    # --- Amérique du Sud (Ligues jeunes) ---
    "arg.u20", "bra.u20", "chi.u19", "col.u19", "par.u19", "uru.u19",

    # --- Afrique ---
    "caf.nations", "caf.nations_qual",
    "caf.champions", "caf.confed",
    "rsa.1",
    "nga.1",
    "gha.1",
    "alg.1",
    "cmr.1",
    "tun.1",
    "mar.1",
    "egy.1",
    "civ.1",
    "sen.1",
    "congo.1",
    "zambia.1",

    # --- Asie ---
    "afc.champions", "afc.cup", "afc.asian.cup",
    "ksa.1",
    "jpn.1", "jpn.2",
    "chn.1", "chn.2",
    "ind.1", "ind.2",
    "tha.1", "tha.2",
    "mys.1",
    "idn.1",
    "sgp.1",
    "vietnam.1",
    "myanmar.1",
    "cambodia.1",
    "bangladesh.1",
    "mongolia.1",
    "bhutan.1",

    # --- Asie (Ligues jeunes) ---
    "jpn.u18", "chn.u19", "ind.u17",

    # --- Océanie ---
    "aus.1", "aus.2",
    "ofc.champions",

    # --- Compétitions féminines ---
    "eng.w.1", "esp.w.1", "fra.w.1", "ned.w.1", "aus.w.1",
    "fifa.wwc", "uefa.wchampions", "concacaf.w.gold",

    # --- Amicales ---
    "club.friendly",
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

def get_stats_for_match(event_id):
    """Récupère les statistiques pour un match spécifique"""
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/summary?event={event_id}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        stats = {
            "home_shots": 0, "away_shots": 0,
            "home_corners": 0, "away_corners": 0,
            "home_possession": 50, "away_possession": 50,
            "home_shots_on_target": 0, "away_shots_on_target": 0,
            "home_attacks": 0, "away_attacks": 0,
        }
        
        if "boxscore" in data:
            for team_stats in data["boxscore"].get("teams", []):
                is_home = team_stats.get("homeAway", "") == "home"
                for stat in team_stats.get("statistics", []):
                    stat_name = stat.get("name", "")
                    stat_value = 0
                    for display in stat.get("displayValue", "").split():
                        if display.replace(".", "").isdigit():
                            stat_value = float(display)
                            break
                    
                    if is_home:
                        if stat_name == "shots": stats["home_shots"] = int(stat_value)
                        elif stat_name == "cornerKicks": stats["home_corners"] = int(stat_value)
                        elif stat_name == "possession": stats["home_possession"] = int(stat_value)
                        elif stat_name == "shotsOnTarget": stats["home_shots_on_target"] = int(stat_value)
                        elif stat_name == "dangerousAttacks": stats["home_attacks"] = int(stat_value)
                    else:
                        if stat_name == "shots": stats["away_shots"] = int(stat_value)
                        elif stat_name == "cornerKicks": stats["away_corners"] = int(stat_value)
                        elif stat_name == "possession": stats["away_possession"] = int(stat_value)
                        elif stat_name == "shotsOnTarget": stats["away_shots_on_target"] = int(stat_value)
                        elif stat_name == "dangerousAttacks": stats["away_attacks"] = int(stat_value)
        
        return stats
    except Exception as e:
        return None

def get_live_matches():
    """Récupère les matchs en direct pour TOUTES les ligues"""
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
                
                stats = get_stats_for_match(event_id)
                if not stats:
                    continue
                
                home_shots = stats["home_shots"]
                away_shots = stats["away_shots"]
                home_corners = stats["home_corners"]
                away_corners = stats["away_corners"]
                home_possession = stats["home_possession"]
                away_possession = stats["away_possession"]
                home_attacks = stats["home_attacks"]
                away_attacks = stats["away_attacks"]
                home_shots_on_target = stats["home_shots_on_target"]
                away_shots_on_target = stats["away_shots_on_target"]
                
                # Score de danger 1MT
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
                
                # Score de danger match
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
            continue
    
    return all_matches

print("🤖 Bot lancé - TOUTES les ligues (avec statistiques)")

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
                        f"🏆 {match['league']}\n"
                        f"⏱️ {minute}' (1MT)\n\n"
                        f"📊 Statistiques:\n"
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
                        f"🏆 {match['league']}\n"
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
        print(f"❌ Erreur: {e}")
        time.sleep(60)
