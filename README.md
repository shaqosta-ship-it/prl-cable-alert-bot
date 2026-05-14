# PRL Cable Knit Alert Bot

Ein einfacher Telegram-Alert-Bot für Vinted-Push-Benachrichtigungen zu Polo Ralph Lauren Cable Knit Pullovern.

## Render Settings

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Environment Variables:

- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID
- WEBHOOK_SECRET

## Test

Öffne im Browser:

```text
https://DEIN-RENDER-LINK.onrender.com/test?secret=DEIN_SECRET
```
