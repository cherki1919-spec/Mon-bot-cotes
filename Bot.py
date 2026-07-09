import requests
from datetime import datetime

TELEGRAM_TOKEN = "8829107151:AAG1JLV9-7AI-H6wugq3YaNE2IIqlrZyxuk"
CHAT_ID = "810719713"
RAPIDAPI_KEY = "da61753fdd0448298657e6e316007677"

URL_BASE = "https://api-football-v1.p.rapidapi.com/v3"
HEADERS = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "api-football-v1.p.rapidapi.com"
}

def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("✅ Message envoyé à Telegram")
    except Exception as e:
        print(f"❌ Erreur d'envoi : {e}")

print("🔍 DIAGNOSTIC - Vérification de l'API...")

try:
    date_aujourdhui = datetime.now().strftime("%Y-%m-%d")
    url = f"{URL_BASE}/fixtures"
    params = {"date": date_aujourdhui}
    
    print(f"📡 Appel API : {url} avec date={date_aujourdhui}")
    reponse = requests.get(url, headers=HEADERS, params=params, timeout=15)
    
    # 🔥 AFFICHE LA RÉPONSE BRUTE (le plus important)
    print(f"📄 Statut HTTP : {reponse.status_code}")
    print(f"📄 Contenu brut (type {type(reponse.text)}) :")
    print(reponse.text[:500])  # Les 500 premiers caractères
    
    # Envoi sur Telegram pour que tu voies même si les logs sont coupés
    envoyer_telegram(f"🔍 DIAGNOSTIC\nStatut: {reponse.status_code}\nRéponse: {reponse.text[:300]}")
    
except Exception as e:
    print(f"❌ Erreur : {e}")
    envoyer_telegram(f"❌ Erreur diagnostic : {e}")
