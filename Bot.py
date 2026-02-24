from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import json
import random
import requests
import os
from datetime import datetime
import asyncio
import lager
from telegram.error import BadRequest

# ==================== CONFIG ====================
TOKEN = "8022437582:AAGxf39INiUqyjKgsNYS_7Vf3hii5c55DCw"

DISCORD_PENDING = "https://discord.com/api/webhooks/1471609900369973280/CP5MxetP45NN2lWhtQ7fy4eDpnOxJQABVngdHCT-UgACEl7Ryhlkaicmy_zZ4W_4HiAb"
DISCORD_PAID = "https://discord.com/api/webhooks/1471610054024105994/65piFxwjXU0zkA5BGK6DxN3q07uxNqOPtAnKsVl8-GBTH08LgGNL8JaWOIc2siQIf-Tc"

ADMINS = [6574712528, 6589321599]
TWINT_NUMMER = "0767985123"
TWINT_BASIS_LINK = "https://go.twint.ch/1/e/tw?tw=acq.wkgkUnWhSHuUgeUJRtdPCwvq1XyXQHKrDSVA93cE9L1W5szrpSWB3HDPDSZ_mbKx"

ABHOL_ADRESSE = "Brunnenhofstrasse 33\nSchlatt TG 8252"
ABHOL_KONTAKT = "076 706 90 27"

GRATIS_UEBERGABE_PLZ = ["8252", "8253", "8254", "8200", "8201", "8203", "8204"]
GRATIS_UEBERGABE_ORT = ["schlatt", "diessenhofen", "basadingen", "schaffhausen", "sh"]

SUMUP_API_KEY = "sup_sk_CewWV3So3nOXI2HvjY2sOYO5aWiHZjfh2"
SUMUP_MERCHANT_CODE = "MDWQMYYV"
SUMUP_API_URL = "https://api.sumup.com/v0.1/checkouts"
SUMUP_RETURN_URL = "https://etha-scandic-apodeictically.ngrok-free.dev/sumup-webhook"

AFFILIATE_PROVISION_PER_VAPE = 3
AFFILIATES_FILE = "affiliates.json"

def lade_affiliates() -> dict:
    if not os.path.exists(AFFILIATES_FILE):
        return {}
    try:
        with open(AFFILIATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def speichere_affiliates(data: dict):
    with open(AFFILIATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

WILLKOMMENS_BILD = "https://hifancyvape.com/wp-content/uploads/2023/10/HIFANCY-Logo1.png"
BILD_50K = "https://hifancypuff.com/wp-content/uploads/2025/11/YK195-banner%E5%9B%BE-3.jpg"
BILD_60K = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSPLAohPdrJjzdmDado9p0W9AtXHU5ce7CJmQ&s"

def neue_bestellnummer():
    return f"LF-{random.randint(100000, 999999)}"

def lade_json(pfad, default):
    if not os.path.exists(pfad):
        return default
    try:
        with open(pfad, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def speichere_json(pfad, daten):
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(daten, f, indent=2, ensure_ascii=False)

def lade_bestellungen():
    return lade_json("bestellungen.json", [])

def speichere_bestellungen(daten):
    speichere_json("bestellungen.json", daten)

def lade_logs():
    return lade_json("logs.json", [])

def speichere_logs(daten):
    speichere_json("logs.json", daten)

def generate_twint_link(preis: float, bestellnr: str):
    zweck = f"Bestellung {bestellnr} LuxeFinds"
    zweck_encoded = zweck.replace(" ", "+")
    return f"{TWINT_BASIS_LINK}&amount={preis:.2f}&trxInfo={zweck_encoded}"

def create_sumup_hosted_checkout(gesamt_preis: float, bestellnr: str) -> tuple[bool, str]:
    if not SUMUP_API_KEY or not SUMUP_MERCHANT_CODE:
        return False, "SumUp nicht konfiguriert"

    headers = {"Authorization": f"Bearer {SUMUP_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "checkout_reference": f"LF-{bestellnr}-{random.randint(1000,9999)}",
        "amount": round(float(gesamt_preis), 2),
        "currency": "CHF",
        "merchant_code": SUMUP_MERCHANT_CODE,
        "return_url": SUMUP_RETURN_URL,
        "hosted_checkout": {"enabled": True}
    }

    try:
        r = requests.post(SUMUP_API_URL, headers=headers, json=payload, timeout=15)
        r.raise_for_status()
        data = r.json()
        hosted_url = data.get("hosted_checkout_url")
        if hosted_url:
            return True, hosted_url
        return False, str(data)
    except Exception as e:
        return False, str(e)

def lade_notify():
    data = lade_json("notify.json", [])
    if not isinstance(data, list):
        print("notify.json war kein Array – wird zurückgesetzt")
        return []
    return data

def speichere_notify(daten):
    speichere_json("notify.json", daten)

def discord_embed(daten, webhook_url, status="IN PRÜFUNG"):
    warenkorb_text = "\n".join(
        [f"• {item['menge']}× {item['produkt']} ({item['preis']:.2f} CHF)"
         for item in daten.get("warenkorb", [])]
    )
    embed = {
        "title": "Neue Bestellung" if status == "IN PRÜFUNG" else f"Status: {status}",
        "color": 0x9b59b6 if status == "IN PRÜFUNG" else (0x2ecc71 if status == "BEZAHLT" else 0xe74c3c),
        "fields": [
            {"name": "Bestellnummer", "value": daten["bestellnr"], "inline": True},
            {"name": "Kunde", "value": daten["user"], "inline": True},
            {"name": "Warenkorb", "value": warenkorb_text, "inline": False},
            {"name": "Gesamt", "value": f"{daten['gesamt_preis']:.2f} CHF", "inline": True},
            {"name": "Methode", "value": daten["zahlung"].upper(), "inline": True},
            {"name": "Status", "value": status, "inline": True},
        ],
        "footer": {"text": "LuxeFinds • " + datetime.now().strftime("%d.%m.%Y %H:%M")},
    }
    if screenshot_url := daten.get("screenshot_url"):
        embed["image"] = {"url": screenshot_url}
    try:
        requests.post(webhook_url, json={"embeds": [embed]})
    except:
        pass

def discord_send_orders_list(bestellungen):
    if not bestellungen:
        embed = {
            "title": "📦 Bestellungen",
            "description": "Aktuell keine Bestellungen vorhanden.",
            "color": 0x7289da,
            "footer": {"text": "LuxeFinds Admin • " + datetime.now().strftime("%d.%m.%Y %H:%M")}
        }
        requests.post(DISCORD_PENDING, json={"embeds": [embed]})
        return

    fields = []
    for b in bestellungen:
        status = b.get("status", "IN PRÜFUNG")
        fields.append({
            "name": f"**{b['bestellnr']}** – {status}",
            "value": (
                f"**Kunde:** {b['user']} (ID: {b['user_id']})\n"
                f"**Gesamt:** {b['gesamt_preis']:.2f} CHF | **Methode:** {b.get('zahlung', 'N/A').upper()}\n"
                f"**Versand:** {b.get('versand_methode', 'N/A')}\n"
                f"**WhatsApp:** {b.get('whatsapp', 'Nicht angegeben')}"
            ),
            "inline": False
        })

    embed = {
        "title": "📦 Aktuelle Bestellungen",
        "color": 0x7289da,
        "fields": fields,
        "footer": {"text": f"{len(bestellungen)} Bestellung(en) • " + datetime.now().strftime("%d.%m.%Y %H:%M")},
        "timestamp": datetime.now().isoformat()
    }
    requests.post(DISCORD_PENDING, json={"embeds": [embed]})

async def zeige_kategorien(update: Update, context: ContextTypes.DEFAULT_TYPE, is_first=False):
    lagerdaten = lager.alle()
    kategorien = sorted(set(p.get("kategorie") for p in lagerdaten.values() if p.get("kategorie")))
    text = "Willkommen bei **LuxeFinds**!\nSchreib /start um den Shop zu starten\nSchreib /bilder um die Produktbilder zu sehen\n\nWähle deine Kategorie:"
    buttons = [[InlineKeyboardButton(k, callback_data=f"kategorie|{k}")] for k in kategorien]

    if update.message or is_first:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    affiliate_code = None
    if args:
        affiliate_code = args[0].strip().upper()
        print(f"[AFFILIATE-TRACKING] User {user_id} kam mit Code: {affiliate_code}")
        await update.message.reply_text(f"[TEST] Affiliate-Code erkannt: {affiliate_code}", parse_mode=None)

    context.user_data["affiliate_code"] = affiliate_code

    context.user_data.clear()
    context.user_data["warenkorb"] = []

    await zeige_kategorien(update, context, is_first=True)

# Der Rest deines Codes (bilder_cmd, screenshot_handler, bezahlt_handler, warenkorb_anzeigen, loeschen_handler, abbruch_handler, clear_chat, orders_cmd, button_handler, text_handler, confirm_cmd, reject_cmd, main()) bleibt exakt so wie in deiner letzten Version

# ==================== MAIN ====================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirm", confirm_cmd))
    app.add_handler(CommandHandler("reject", reject_cmd))
    app.add_handler(CommandHandler("clearchat", clear_chat))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CommandHandler("bilder", bilder_cmd))
    app.add_handler(CommandHandler("bild", bilder_cmd))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    app.add_handler(MessageHandler(filters.Regex(r"(?i)^bezahlt$"), bezahlt_handler))

    print("LuxeFinds Bot läuft – mit Affiliate-Tracking")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    from flask import Flask, request
    from threading import Thread
    import os

    flask_app = Flask(__name__)

    @flask_app.route('/health')
    def health():
        return "OK", 200

    last_payload = None

    @flask_app.route('/sumup-webhook', methods=['GET', 'POST'])
    def sumup_webhook():
        global last_payload
        if request.method == 'GET':
            checkout_reference = request.args.get('checkout_reference', 'unbekannt')
            status = request.args.get('status', 'unbekannt')
            print(f"[SUMUP REDIRECT] GET | Ref: {checkout_reference} | Status: {status}")
            return """
            <html>
            <head><title>Zahlung abgeschlossen</title></head>
            <body style="text-align:center; padding:80px; font-family:Arial;">
                <h1>✅ Vielen Dank!</h1>
                <p>Deine Zahlung wurde verarbeitet.</p>
                <p>Gehe zurück zum Bot – er prüft automatisch.</p>
                <a href="https://t.me/LuxeFinds_Bot" style="font-size:22px; padding:15px 30px; background:#4CAF50; color:white; border-radius:8px; text-decoration:none;">Zum Bot →</a>
            </body>
            </html>
            """, 200

        elif request.method == 'POST':
            try:
                data = request.get_json()
                last_payload = data
                print("\n" + "="*80)
                print("SUMUP NOTIFICATION ERHALTEN!")
                print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("Payload:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("="*80 + "\n")
                return "OK", 200
            except Exception as e:
                print(f"Webhook Fehler: {str(e)}")
                return "Fehler", 400

    port = int(os.environ.get("PORT", 10000))
    Thread(target=flask_app.run, kwargs={'host': '0.0.0.0', 'port': port, 'debug': False}).start()
    main()
