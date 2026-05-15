import os
import re
from datetime import datetime, timezone

import requests
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

# Preislogik für Polo Ralph Lauren Cable Knit Pullover.
# Diese Werte kannst du später anpassen.
PRICE_RULES = {
    "cotton": {
    "name": "Polo Ralph Lauren Cable Knit Pullover Baumwolle",
    "optimal_buy": 12,
    "sweet_spot_buy": 20,
    "max_buy": 30,
    "absolute_worst_case_resale": 28,
    "expected_resale_low": 35,
    "expected_resale_high": 50,
},
    "cashmere_wool": {
    "name": "Polo Ralph Lauren Cable Knit Cashmere/Wool Pullover",
    "optimal_buy": 20,
    "sweet_spot_buy": 35,
    "max_buy": 45,
    "absolute_worst_case_resale": 45,
    "expected_resale_low": 60,
    "expected_resale_high": 90,
},
}

INCLUDE_WORDS = [
    "polo ralph lauren",
    "ralph lauren",
    "prl",
]

CABLE_WORDS = [
    "cable knit",
    "cable-knit",
    "cableknit",
    "zopfmuster",
    "zopfstrick",
    "strickpullover",
    "knit pullover",
    "knitted sweater",
    "cable sweater",
    "cable jumper",
]

EXCLUDE_WORDS = [
    "lauren ralph lauren",
    "chaps",
    "us polo",
    "u.s. polo",
    "uspa",
    "fake",
    "fälschung",
    "replica",
    "replika",
    "loch",
    "löcher",
    "defekt",
    "kaputt",
    "fleck",
    "flecken",
    "shrunk",
    "eingelaufen",
]

CASHMERE_WOOL_WORDS = [
    "cashmere",
    "kaschmir",
    "wool",
    "wolle",
    "merino",
]


def clean(text: str) -> str:
    return text.lower().replace("’", "'").strip()


def has_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def extract_price(text: str):
    """Erkennt z. B. 25 €, 25,00 €, €25, 25.00€."""
    patterns = [
        r"(\d{1,4}(?:[,.]\d{1,2})?)\s?€",
        r"€\s?(\d{1,4}(?:[,.]\d{1,2})?)",
        r"(\d{1,4}(?:[,.]\d{1,2})?)\s?eur",
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return float(match.group(1).replace(",", "."))
    return None


def detect_item_type(text: str):
    t = clean(text)

    if has_any(t, EXCLUDE_WORDS):
        return None, "exclude"

    brand_ok = has_any(t, INCLUDE_WORDS)
    cable_ok = has_any(t, CABLE_WORDS)

    if not brand_ok or not cable_ok:
        return None, "no_match"

    if has_any(t, CASHMERE_WOOL_WORDS):
        return PRICE_RULES["cashmere_wool"], "match"

    return PRICE_RULES["cotton"], "match"


def score(price, rule):
    if price is None:
        return "👀 PREIS NICHT ERKANNT", 5, "Ich habe keinen Preis in der Notification gefunden. Manuell prüfen."

    if price <= rule["optimal_buy"]:
        return "🔥 SOFORT CHECKEN", 10, "Preis liegt im optimalen Einkaufsbereich."
    if price <= rule["sweet_spot_buy"]:
        return "✅ GUTER DEAL", 8, "Preis liegt im Sweet-Spot-Einkaufsbereich."
    if price <= rule["max_buy"]:
        return "⚠️ NUR MIT GUTEM ZUSTAND", 6, "Preis ist noch kaufbar, aber Zustand, Größe und Farbe müssen passen."
    return "❌ WAHRSCHEINLICH ZU TEUER", 3, "Preis liegt über deinem Max-Buy für schnelles Reselling."


def euro(value):
    return f"{value:.2f} €".replace(".", ",")


def send_telegram(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram ENV Variablen fehlen.")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=10,
    )
    if response.status_code >= 400:
        raise RuntimeError(response.text)


def build_message(title: str, body: str, big_text: str, app_name: str):
    full_text = f"{title}\n{body}\n{big_text}"
    rule, status = detect_item_type(full_text)

    if status == "exclude":
        return None, "Blacklist-Wort gefunden"
    if status == "no_match":
        return None, "Kein Polo Ralph Lauren Cable Knit Treffer"

    price = extract_price(full_text)
    label, score_number, reason = score(price, rule)

    if price is None:
        margin_text = "Marge: Preis nicht erkannt"
        price_text = "nicht erkannt"
    else:
        conservative_margin = rule["expected_resale_low"] - price
        good_margin = rule["expected_resale_high"] - price
        worst_margin = rule["absolute_worst_case_resale"] - price
        price_text = euro(price)
        margin_text = (
            f"Konservative Bruttomarge: {euro(conservative_margin)}\n"
            f"Gute Bruttomarge: {euro(good_margin)}\n"
            f"Worst-Case-Bruttomarge: {euro(worst_margin)}"
        )

    message = (
        f"{label}\n"
        f"Score: {score_number}/10\n\n"
        f"📦 Modell: {rule['name']}\n"
        f"💸 Erkannter Preis: {price_text}\n\n"
        f"📊 Deine Einkaufs-Preislogik:\n"
        f"Optimaler Kaufpreis: bis {rule['optimal_buy']} €\n"
        f"Sweet Spot Kaufpreis: bis {rule['sweet_spot_buy']} €\n"
        f"Maximaler Kaufpreis: bis {rule['max_buy']} €\n"
        f"Absolute Worst-Case Exit: {rule['absolute_worst_case_resale']} €\n"
        f"Erwarteter Verkauf: {rule['expected_resale_low']}–{rule['expected_resale_high']} €\n\n"
        f"💰 {margin_text}\n\n"
        f"🧠 Einschätzung: {reason}\n\n"
        f"🔔 App: {app_name}\n"
        f"Titel: {title}\n"
        f"Text: {body}\n"
        f"Big Text: {big_text}\n\n"
        f"➡️ Jetzt Vinted öffnen und manuell prüfen: Zustand, Materialetikett, Maße, Verkäuferbewertungen."
    )
    return message, "sent"


def check_secret(secret: str | None):
    if not WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="WEBHOOK_SECRET fehlt auf dem Server")
    if secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Falsches Secret")


@app.get("/")
def home():
    return {
        "ok": True,
        "bot": "PRL Cable Knit Alert Bot",
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/test")
def test(secret: str):
    check_secret(secret)
    message, reason = build_message(
        title="Test: Neuer Artikel auf Vinted",
        body="Polo Ralph Lauren Cable Knit Pullover Navy Größe L 25 €",
        big_text="Baumwolle, sehr guter Zustand",
        app_name="Vinted Test",
    )
    if message:
        send_telegram(message)
    return {"ok": True, "reason": reason}


@app.post("/vinted-alert")
async def vinted_alert(request: Request, secret: str | None = None):
    check_secret(secret)
    data = await request.json()

    title = str(data.get("title", ""))
    body = str(data.get("body", ""))
    big_text = str(data.get("big_text", ""))
    app_name = str(data.get("app", ""))

    message, reason = build_message(title, body, big_text, app_name)

    if message:
        send_telegram(message)
        return {"ok": True, "sent": True, "reason": reason}

    return {"ok": True, "sent": False, "reason": reason}
