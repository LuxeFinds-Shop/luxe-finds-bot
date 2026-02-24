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

async def bilder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Hier sind die Produktbilder:\n\n50K Vape:\n60K Vape:"
    buttons = [
        [InlineKeyboardButton("Zurueck zu Kategorien", callback_data="zurueck_kategorien")]
    ]

    await update.message.reply_photo(
        photo=BILD_50K,
        caption="50K Vape",
        parse_mode="Markdown"
    )
    await update.message.reply_photo(
        photo=BILD_60K,
        caption="60K Vape",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("status") != "awaiting_proof":
        return
    if not update.message.photo:
        return
    photo = update.message.photo[-1]
    file = await photo.get_file()
    context.user_data["screenshot_url"] = file.file_path

async def bezahlt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower().strip() != "bezahlt":
        return
    if context.user_data.get("status") != "awaiting_proof":
        return
    if not context.user_data.get("screenshot_url"):
        await update.message.reply_text(
            "Bitte sende zuerst den Screenshot deiner Zahlung.\n"
            "Erst danach schreibe „bezahlt“."
        )
        return

    warenkorb = context.user_data.get("warenkorb", [])
    gesamt_preis = context.user_data.get("gesamt_preis")
    bestellnr = context.user_data.get("bestellnr")
    daten = {
        "user": update.message.from_user.full_name,
        "user_id": update.message.from_user.id,
        "warenkorb": warenkorb,
        "gesamt_preis": gesamt_preis,
        "bestellnr": bestellnr,
        "adresse": context.user_data.get("confirmed_adresse", context.user_data.get("adresse", "")),
        "whatsapp": context.user_data.get("confirmed_whatsapp", context.user_data.get("whatsapp", "")),
        "zeit": datetime.now().isoformat(),
        "screenshot_url": context.user_data.get("screenshot_url"),
        "zahlung": context.user_data.get("zahlung"),
        "versand_methode": context.user_data.get("versand_methode", "standard"),
        "affiliate_code": context.user_data.get("affiliate_code")
    }
    bestellungen = lade_bestellungen()
    bestellungen.append(daten)
    speichere_bestellungen(bestellungen)
    discord_embed(daten, webhook_url=DISCORD_PENDING, status="IN PRÜFUNG")

    aff_code = context.user_data.get("affiliate_code")
    if aff_code:
        try:
            affiliates = lade_affiliates()
            affiliate_id = None
            for uid, aff in affiliates.items():
                if aff.get("code", "").upper() == aff_code.upper():
                    affiliate_id = uid
                    break

            if affiliate_id:
                vape_count = sum(item.get("menge", 0) for item in daten.get("warenkorb", []))
                provision = vape_count * AFFILIATE_PROVISION_PER_VAPE

                current_balance = affiliates[affiliate_id].get("balance", 0.0)
                new_balance = round(current_balance + provision, 2)
                affiliates[affiliate_id]["balance"] = new_balance

                speichere_affiliates(affiliates)

                await context.bot.send_message(
                    chat_id=int(affiliate_id),
                    text=(
                        f"🎉 Neue Provision gutgeschrieben!\n\n"
                        f"Bestellung: {bestellnr}\n"
                        f"Vapes verkauft: {vape_count}\n"
                        f"Provision: +{provision:.2f} CHF\n"
                        f"Neuer Saldo: {new_balance:.2f} CHF"
                    ),
                    parse_mode="Markdown"
                )

                print(f"[PROVISION] {provision:.2f} CHF an {affiliate_id} für Bestellung {bestellnr}")
        except Exception as e:
            print(f"Affiliate-Tracking Fehler: {e}")

    context.user_data["status"] = "waiting_review"
    await update.message.reply_text(
        "Vielen Dank für deine Bestellung!\n\n"
        "Wir haben deinen Zahlungsnachweis erhalten und prüfen ihn umgehend.\n"
        f"Voraussichtliche Bearbeitungszeit: **ca. 30 Minuten**\n\n"
        "Du wirst automatisch benachrichtigt, sobald alles erledigt ist.\n"
        "Bei Fragen stehen wir jederzeit zur Verfügung.",
        parse_mode="Markdown"
    )
    for admin in ADMINS:
        warenkorb_text = "\n".join(
            [f"• {item['menge']}× {item['produkt']} ({item['preis']:.2f} CHF)"
             for item in warenkorb]
        )
        await context.bot.send_message(
            admin,
            f"🧾 **Neue Bestellung eingegangen**\n\n"
            f"Bestellnummer: `{bestellnr}`\n"
            f"Warenkorb:\n{warenkorb_text}\n\n"
            f"Gesamt: **{gesamt_preis:.2f} CHF**\n"
            f"Methode: {daten['zahlung'].upper()}\n"
            f"Versand: {daten['versand_methode']}\n"
            f"Kunde: {daten['user']} (ID: {daten['user_id']})\n"
            f"Adresse: {daten['adresse']}\n"
            f"WhatsApp: {daten['whatsapp']}\n\n"
            f"→ Bestätigen: `/confirm {bestellnr}`\n"
            f"→ Ablehnen:   `/reject {bestellnr}`",
            parse_mode="Markdown"
        )

async def confirm_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("❌ Nutzung: /confirm LF-XXXXXX")
        return
    bestellnr = context.args[0]
    bestellungen = lade_bestellungen()
    ziel = next((b for b in bestellungen if b.get("bestellnr") == bestellnr), None)
    if not ziel:
        await update.message.reply_text("❌ Bestellung nicht gefunden.")
        return
    logs = lade_logs()
    logs.append({**ziel, "status": "BESTÄTIGT", "admin": update.effective_user.id})
    speichere_logs(logs)
    await context.bot.send_message(
        chat_id=ziel["user_id"],
        text=
            "✅ **Deine Zahlung wurde bestätigt!**\n\n"
            "Vielen Dank für deinen Einkauf bei LuxeFinds.\n"
            "Du wirst innerhalb der nächsten 24 Stunden von uns kontaktiert.\n"
            "Bitte sende uns deine WhatsApp-Nummer für die Lieferung.",
        parse_mode="Markdown"
    )
    discord_embed(ziel, webhook_url=DISCORD_PAID, status="BESTÄTIGT")

async def reject_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        await update.message.reply_text("❌ Nutzung: /reject LF-XXXXXX")
        return
    bestellnr = context.args[0]
    bestellungen = lade_bestellungen()
    ziel = next((b for b in bestellungen if b.get("bestellnr") == bestellnr), None)
    if not ziel:
        await update.message.reply_text("❌ Bestellung nicht gefunden.")
        return
    try:
        for item in ziel.get("warenkorb", []):
            lager.erhoehen(item["produkt"], item["menge"])
    except:
        pass
    logs = lade_logs()
    logs.append({**ziel, "status": "ABGELEHNT", "admin": update.effective_user.id})
    speichere_logs(logs)
    await context.bot.send_message(
        chat_id=ziel["user_id"],
        text=
            "❌ **Deine Bestellung wurde leider abgelehnt.**\n\n"
            "Bitte kontaktiere unseren Support für weitere Informationen.\n"
            "Wir entschuldigen uns für die Unannehmlichkeiten.",
        parse_mode="Markdown"
    )
    discord_embed(ziel, webhook_url=DISCORD_PENDING, status="ABGELEHNT")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id

    deleted = 0
    for i in range(1, 151):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id - i)
            deleted += 1
        except:
            continue

    try:
        await update.effective_message.delete()
    except:
        pass

    if deleted > 0:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"Chatverlauf so weit wie möglich gelöscht ({deleted} Nachrichten)."
        )
        await asyncio.sleep(4)
        try:
            await msg.delete()
        except:
            pass
    else:
        await update.message.reply_text("Keine Nachrichten zum Löschen gefunden.")

async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("Du hast keine Berechtigung für diesen Befehl.")
        return

    bestellungen = lade_bestellungen()
    discord_send_orders_list(bestellungen)

    await update.message.reply_text(
        "Die Bestellliste wurde an Discord gesendet.",
        parse_mode="Markdown"
    )

async def warenkorb_anzeigen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    warenkorb = context.user_data.get("warenkorb", [])
    gesamt_preis = sum(item["preis"] * item["menge"] for item in warenkorb) if warenkorb else 0
    text = "Dein Warenkorb:\n\n"
    buttons = []
    if warenkorb:
        for i, item in enumerate(warenkorb):
            text += f"• {item['menge']}× {item['produkt']} – {item['preis']:.2f} CHF\n"
            buttons.append([
                InlineKeyboardButton(
                    f"× Entfernen: {item['produkt']} ({item['menge']}×)",
                    callback_data=f"loeschen|{i}"
                )
            ])
        text += f"\n**Gesamt: {gesamt_preis:.2f} CHF**"
        buttons.append([InlineKeyboardButton("Zur Zahlung gehen", callback_data="adresse_abfrage")])
    else:
        text = "Dein Warenkorb ist leer.\n\nWas möchtest du tun?"
    buttons.append([InlineKeyboardButton("Zurück zu Produkten", callback_data="zurueck_kategorien")])
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def loeschen_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if '|' not in query.data:
        await query.edit_message_text("Fehler beim Löschen.")
        return
    _, index_str = query.data.split("|", 1)
    try:
        index = int(index_str)
    except ValueError:
        await query.edit_message_text("Fehler beim Löschen.")
        return
    warenkorb = context.user_data.get("warenkorb", [])
    if index < 0 or index >= len(warenkorb):
        await query.edit_message_text("Position nicht gefunden.")
        return
    entfernt = warenkorb.pop(index)
    await query.edit_message_text(f"Entfernt: {entfernt['menge']}× {entfernt['produkt']}")
    try:
        lager.erhoehen(entfernt['produkt'], entfernt['menge'])
    except Exception as e:
        print(f"Fehler beim Zurückzählen: {e}")
    await warenkorb_anzeigen(update, context)

async def abbruch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    warenkorb = context.user_data.get("warenkorb", [])
    if not warenkorb:
        await query.edit_message_text("Warenkorb ist leer – nichts abzubrechen.")
        return
    for item in warenkorb:
        try:
            lager.erhoehen(item['produkt'], item['menge'])
        except Exception as e:
            print(f"Fehler beim Abbruch-Zurückzählen: {e}")
    context.user_data["warenkorb"] = []
    context.user_data.pop("bestellnr", None)
    context.user_data.pop("gesamt_preis", None)
    context.user_data.pop("zahlung", None)
    context.user_data.pop("status", None)
    await query.edit_message_text(
        "Schade dass du die Bestellung abgebrochen hast.\n"
        "Wir sind für dich immer da – wenn du neu bestellen willst,\n"
        "drücke einfach auf den Button **Neue Bestellung**.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Neue Bestellung", callback_data="zurueck_kategorien")]
        ]),
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "warenkorb":
        await warenkorb_anzeigen(update, context)
        return

    if data == "zurueck_kategorien":
        await zeige_kategorien(update, context)
        return

    if data == "abbruch_bestellung":
        await abbruch_handler(update, context)
        return

    if data == "confirm_bargeld":
        warenkorb = context.user_data.get("warenkorb", [])
        gesamt_preis = context.user_data.get("gesamt_preis")
        bestellnr = context.user_data.get("bestellnr")
        daten = {
            "user": update.effective_user.full_name,
            "user_id": update.effective_user.id,
            "warenkorb": warenkorb,
            "gesamt_preis": gesamt_preis,
            "bestellnr": bestellnr,
            "adresse": context.user_data.get("confirmed_adresse", ""),
            "whatsapp": context.user_data.get("confirmed_whatsapp", ""),
            "zeit": datetime.now().isoformat(),
            "zahlung": "BARGAELD",
            "versand_methode": context.user_data.get("versand_methode", "selbstabholung"),
            "status": "IN PRÜFUNG",
            "affiliate_code": context.user_data.get("affiliate_code")
        }
        bestellungen = lade_bestellungen()
        bestellungen.append(daten)
        speichere_bestellungen(bestellungen)
        discord_embed(daten, webhook_url=DISCORD_PENDING, status="IN PRÜFUNG")

        aff_code = context.user_data.get("affiliate_code")
        if aff_code:
            try:
                affiliates = lade_affiliates()
                affiliate_id = None
                for uid, aff in affiliates.items():
                    if aff.get("code", "").upper() == aff_code.upper():
                        affiliate_id = uid
                        break

                if affiliate_id:
                    vape_count = sum(item.get("menge", 0) for item in daten.get("warenkorb", []))
                    provision = vape_count * AFFILIATE_PROVISION_PER_VAPE

                    current_balance = affiliates[affiliate_id].get("balance", 0.0)
                    new_balance = round(current_balance + provision, 2)
                    affiliates[affiliate_id]["balance"] = new_balance

                    speichere_affiliates(affiliates)

                    await context.bot.send_message(
                        chat_id=int(affiliate_id),
                        text=(
                            f"🎉 Neue Provision gutgeschrieben!\n\n"
                            f"Bestellung: {bestellnr}\n"
                            f"Vapes verkauft: {vape_count}\n"
                            f"Provision: +{provision:.2f} CHF\n"
                            f"Neuer Saldo: {new_balance:.2f} CHF"
                        ),
                        parse_mode="Markdown"
                    )

                    print(f"[PROVISION] {provision:.2f} CHF an {affiliate_id} für Bestellung {bestellnr}")
            except Exception as e:
                print(f"Affiliate-Tracking Fehler in confirm_bargeld: {e}")

        await query.edit_message_text(
            f"**Bestellung {bestellnr} bestätigt!**\n\n"
            "Vielen Dank! Wir haben deine Bargeld-Bestellung erhalten.\n"
            "Wir kontaktieren dich per WhatsApp für die Abholung/Übergabe.\n\n"
            "Bei Fragen: 076 706 90 27",
            parse_mode="Markdown"
        )

        for admin in ADMINS:
            await context.bot.send_message(
                admin,
                f"💵 **Neue BARGAELD-Bestellung!**\n\n"
                f"Bestellnummer: `{bestellnr}`\n"
                f"Gesamt: {gesamt_preis:.2f} CHF\n"
                f"Versand: {daten['versand_methode']}\n"
                f"Kunde: {daten['user']} (ID: {daten['user_id']})\n"
                f"Adresse: {daten['adresse']}\n"
                f"WhatsApp: {daten['whatsapp']}\n\n"
                f"→ Bestätigen: `/confirm {bestellnr}`\n"
                f"→ Ablehnen: `/reject {bestellnr}`",
                parse_mode="Markdown"
            )

        context.user_data.clear()
        return

    if data == "adresse_abfrage":
        if context.user_data.get("confirmed_adresse") and context.user_data.get("confirmed_whatsapp"):
            warenkorb = context.user_data.get("warenkorb", [])
            gesamt_preis = sum(item["preis"] * item["menge"] for item in warenkorb)
            text = "Dein Warenkorb:\n"
            for item in warenkorb:
                text += f"• {item['menge']}× {item['produkt']} – {item['preis']:.2f} CHF\n"
            text += f"\n**Gesamt: {gesamt_preis:.2f} CHF**\n\nWähle deine Versand- / Abhol-Option:"

            adresse = context.user_data.get("confirmed_adresse", "").lower()
            ist_gratis_region = any(plz in adresse for plz in GRATIS_UEBERGABE_PLZ) or any(ort in adresse for ort in GRATIS_UEBERG_ORT)

            buttons = [
                [InlineKeyboardButton("Standard-Versand (7 CHF)", callback_data="versand|standard")],
                [InlineKeyboardButton("Selbstabholung (0 CHF)", callback_data="versand|selbstabholung")]
            ]
            if ist_gratis_region:
                buttons.insert(0, [InlineKeyboardButton("Persönliche Übergabe (gratis)", callback_data="versand|persoenlich")])

            buttons.append([InlineKeyboardButton("← Zum Warenkorb", callback_data="warenkorb")])

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )
        else:
            context.user_data["status"] = "awaiting_address"
            text = "Bitte sende uns deine **Lieferadresse** und **WhatsApp-Nummer** (kann auch in zwei separaten Nachrichten kommen).\nBeispiel:\n\nMusterweg 5\n8000 Zürich\n+41 76 987 65 43"
            buttons = [[InlineKeyboardButton("← Zurück zum Warenkorb", callback_data="warenkorb")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
        return

    if data == "sumup_check":
        await query.edit_message_text(
            "Danke für deine Zahlung!\n\n"
            "Wir überprüfen dies im System – einen Moment bitte...",
            parse_mode="Markdown"
        )

        await asyncio.sleep(6)

        current_reference = context.user_data.get("bestellnr", None)
        last_payload = context.bot_data.get("last_sumup_payload", None)

        is_success = False
        if current_reference and last_payload:
            payload_reference = last_payload.get("checkout_reference", "")
            if payload_reference.startswith(f"LF-{current_reference}-") and last_payload.get("status") == "SUCCESSFUL":
                is_success = True

        if is_success:
            warenkorb = context.user_data.get("warenkorb", [])
            gesamt_preis = context.user_data.get("gesamt_preis")
            bestellnr = context.user_data.get("bestellnr")
            versand_methode = context.user_data.get("versand_methode", "standard")
            daten = {
                "user": update.effective_user.full_name,
                "user_id": update.effective_user.id,
                "warenkorb": warenkorb,
                "gesamt_preis": gesamt_preis,
                "bestellnr": bestellnr,
                "adresse": context.user_data.get("confirmed_adresse", ""),
                "whatsapp": context.user_data.get("confirmed_whatsapp", ""),
                "zeit": datetime.now().isoformat(),
                "screenshot_url": None,
                "zahlung": "sumup",
                "versand_methode": versand_methode,
                "affiliate_code": context.user_data.get("affiliate_code"),
                "status": "BEZAHLT"
            }

            bestellungen = lade_bestellungen()
            bestellungen.append(daten)
            speichere_bestellungen(bestellungen)

            discord_embed(daten, webhook_url=DISCORD_PAID, status="BEZAHLT")

            aff_code = context.user_data.get("affiliate_code")
            if aff_code:
                try:
                    affiliates = lade_affiliates()
                    affiliate_id = None
                    for uid, aff in affiliates.items():
                        if aff.get("code", "").upper() == aff_code.upper():
                            affiliate_id = uid
                            break

                    if affiliate_id:
                        vape_count = sum(item.get("menge", 0) for item in daten.get("warenkorb", []))
                        provision = vape_count * AFFILIATE_PROVISION_PER_VAPE

                        current_balance = affiliates[affiliate_id].get("balance", 0.0)
                        new_balance = round(current_balance + provision, 2)
                        affiliates[affiliate_id]["balance"] = new_balance

                        speichere_affiliates(affiliates)

                        await context.bot.send_message(
                            chat_id=int(affiliate_id),
                            text=(
                                f"🎉 Neue Provision gutgeschrieben!\n\n"
                                f"Bestellung: {bestellnr}\n"
                                f"Vapes verkauft: {vape_count}\n"
                                f"Provision: +{provision:.2f} CHF\n"
                                f"Neuer Saldo: {new_balance:.2f} CHF"
                            ),
                            parse_mode="Markdown"
                        )

                        print(f"[PROVISION] {provision:.2f} CHF an {affiliate_id} für Bestellung {bestellnr}")
                except Exception as e:
                    print(f"Affiliate-Tracking Fehler in sumup_check: {e}")

            await query.edit_message_text(
                "✅ **Zahlung erfolgreich bestätigt!**\n\n"
                "Vielen Dank für deinen Einkauf bei LuxeFinds.\n"
                "Wir bereiten alles vor und kontaktieren dich per WhatsApp.\n"
                "Bei Fragen: 076 706 90 27",
                parse_mode="Markdown"
            )

            context.user_data.clear()
            context.bot_data.pop("last_sumup_payload", None)

        else:
            await query.edit_message_text(
                "❌ **Zahlung konnte nicht bestätigt werden.**\n\n"
                "Bitte versuche es erneut oder wähle eine andere Methode.\n"
                "Falls du denkst, es war erfolgreich – schreibe uns bitte.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Erneut versuchen", callback_data="pay|sumup")],
                    [InlineKeyboardButton("Abbrechen", callback_data="abbruch_bestellung")]
                ]),
                parse_mode="Markdown"
            )

    elif "|" not in data:
        await query.edit_message_text("Ungültiger Button – bitte neu starten mit /start.")
        return

    typ, value = data.split("|", 1)

    if typ == "kategorie":
        lagerdaten = lager.alle()
        buttons = []
        hat_produkte = False

        for name, p in lagerdaten.items():
            if p.get("kategorie") == value and p.get("menge", 0) > 0:
                buttons.append([
                    InlineKeyboardButton(
                        f"{name} – {p.get('preis')} CHF (noch {p.get('menge')})",
                        callback_data=f"produkt|{name}"
                    )
                ])
                hat_produkte = True

        if not hat_produkte:
            text = f"Momentan haben wir nichts an Lager in **{value}**.\n\nMöchtest du benachrichtigt werden, sobald etwas nachgeliefert wird?"
            buttons = [
                [InlineKeyboardButton("Ja – Benachrichtige mich", callback_data=f"notify_ja|{value}")],
                [InlineKeyboardButton("Nein – zurück zu Kategorien", callback_data="zurueck_kategorien")]
            ]
        else:
            text = f"Verfügbare Produkte in **{value}**"
            if context.user_data.get("warenkorb"):
                buttons.append([InlineKeyboardButton("🛒 Zum Warenkorb", callback_data="warenkorb")])
            buttons.append([InlineKeyboardButton("← Zurück zu Kategorien", callback_data="zurueck_kategorien")])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    elif typ == "notify_ja":
        kategorie = value
        user_id = update.effective_user.id

        notify_list = lade_notify()

        if not isinstance(notify_list, list):
            notify_list = []

        if not any(n["user_id"] == user_id and n["kategorie"] == kategorie for n in notify_list):
            notify_list.append({"user_id": user_id, "kategorie": kategorie})
            speichere_notify(notify_list)

        await query.edit_message_text(
            f"Super! Wir benachrichtigen dich, sobald etwas in **{kategorie}** wieder verfügbar ist. 😊",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Zurück zu Kategorien", callback_data="zurueck_kategorien")]
            ]),
            parse_mode="Markdown"
        )

    elif typ == "produkt":
        produkt = value
        info = lager.holen(produkt)
        context.user_data["aktuelles_produkt"] = produkt
        context.user_data["aktueller_preis"] = info.get("preis", 0)
        context.user_data["wartet_auf_menge"] = True
        await query.edit_message_text(
            f"**{produkt}**\n"
            f"Preis: {info.get('preis')} CHF\n"
            f"Noch **{info.get('menge')} Stück** verfügbar\n\n"
            "Wie viele Stück möchtest du?",
            parse_mode="Markdown"
        )

    elif typ == "mehr_produkt":
        if value == "ja":
            await zeige_kategorien(update, context)
        else:
            warenkorb = context.user_data.get("warenkorb", [])
            gesamt_preis = sum(item["preis"] * item["menge"] for item in warenkorb)
            text = "Dein Warenkorb:\n"
            for item in warenkorb:
                text += f"• {item['menge']}× {item['produkt']} – {item['preis']:.2f} CHF\n"
            text += f"\n**Gesamt: {gesamt_preis:.2f} CHF**\n\nWähle deine Zahlungsmethode:"
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("TWINT", callback_data="pay|twint")],
                    [InlineKeyboardButton("Kreditkarte", callback_data="pay|sumup")]
                ]),
                parse_mode="Markdown"
            )

    elif typ == "versand":
        methode = value
        warenkorb = context.user_data.get("warenkorb", [])
        if not warenkorb:
            await query.edit_message_text("Dein Warenkorb ist leer.")
            return

        gesamt_preis = sum(item["preis"] * item["menge"] for item in warenkorb)
        versand_kosten = 0
        versand_text = ""

        if methode == "standard":
            versand_kosten = 7
            versand_text = "Standard-Versand (+7 CHF)"
        elif methode == "persoenlich":
            adresse = context.user_data.get("confirmed_adresse", "").lower()
            ist_gratis_region = any(plz in adresse for plz in GRATIS_UEBERGABE_PLZ) or any(ort in adresse for ort in GRATIS_UEBERG_ORT)
            if not ist_gratis_region:
                await query.edit_message_text(
                    "Persönliche Übergabe ist nur in Diessenhofen, Basadingen, Schlatt TG, Schaffhausen (SH) gratis.\n"
                    "Wähle bitte eine andere Option.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("← Zurück zur Auswahl", callback_data="adresse_abfrage")]
                    ]),
                    parse_mode="Markdown"
                )
                return
            versand_kosten = 0
            versand_text = "Persönliche Übergabe (gratis)"
        elif methode == "selbstabholung":
            versand_kosten = 0
            versand_text = "Selbstabholung (0 CHF)"

        gesamt_mit_versand = gesamt_preis + versand_kosten

        bestellnr = neue_bestellnummer()
        context.user_data["bestellnr"] = bestellnr
        context.user_data["gesamt_preis"] = gesamt_mit_versand
        context.user_data["versand_methode"] = methode
        context.user_data["versand_kosten"] = versand_kosten
        context.user_data["zahlung"] = None
        context.user_data["status"] = "awaiting_payment"

        text = (
            f"**Zusammenfassung**\n"
            f"{versand_text}\n"
            f"Gesamtpreis inkl. Versand: **{gesamt_mit_versand:.2f} CHF**\n\n"
            "Wähle deine Zahlungsmethode:"
        )

        buttons = [
            [InlineKeyboardButton("TWINT", callback_data="pay|twint")],
            [InlineKeyboardButton("Kreditkarte", callback_data="pay|sumup")]
        ]

        if methode in ["persoenlich", "selbstabholung"]:
            buttons.append([InlineKeyboardButton("Bargeld (bei Abholung/Übergabe)", callback_data="pay|bargeld")])

        buttons.append([InlineKeyboardButton("← Zurück", callback_data="adresse_abfrage")])

        if methode == "selbstabholung":
            text += f"\n\n**Abholadresse:**\n{ABHOL_ADRESSE}\nBei Fragen oder Hilfe: {ABHOL_KONTAKT}"

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    elif typ == "pay":
        methode = value
        warenkorb = context.user_data.get("warenkorb", [])
        if not warenkorb:
            await query.edit_message_text("Dein Warenkorb ist leer.")
            return

        gesamt_preis = context.user_data.get("gesamt_preis")
        bestellnr = context.user_data.get("bestellnr")
        versand_methode = context.user_data.get("versand_methode", "standard")

        if methode == "bargeld":
            context.user_data["zahlung"] = methode
            context.user_data["status"] = "awaiting_confirm_bargeld"

            text = (
                f"**Bestellung mit Bargeld-Zahlung**\n\n"
                f"Bestellnummer: `{bestellnr}`\n"
                f"Gesamtbetrag: **{gesamt_preis:.2f} CHF**\n\n"
                "Zahlung erfolgt in bar bei Abholung oder Übergabe.\n"
                "Bitte bring den Betrag passend mit.\n\n"
                f"**Abholadresse:**\n{ABHOL_ADRESSE}\nBei Fragen oder Hilfe: {ABHOL_KONTAKT}"
            )

            buttons = [
                [InlineKeyboardButton("Bestellung bestätigen", callback_data="confirm_bargeld")],
                [InlineKeyboardButton("Bestellung abbrechen", callback_data="abbruch_bestellung")]
            ]

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )

        elif methode == "sumup":
            success, result = create_sumup_hosted_checkout(gesamt_preis, bestellnr)

            context.user_data["zahlung"] = "sumup"
            context.user_data["status"] = "awaiting_sumup_auto"

            if success:
                text = (
                    "💳 **Kreditkarte / Apple Pay / Google Pay – sicher über SumUp**\n\n"
                    f"Bestellnummer: `{bestellnr}`\n"
                    f"Gesamtbetrag: **{gesamt_preis:.2f} CHF**\n\n"
                    f"[Jetzt bezahlen → SumUp öffnen]({result})\n\n"
                    "Nach der Zahlung kommst du zurück.\n"
                    "Drücke dann einfach den Button unten – der Bot prüft automatisch!"
                )

                buttons = [[InlineKeyboardButton("Ich habe bezahlt", callback_data="sumup_check")]]
            else:
                text = (
                    f"❌ **SumUp-Zahlungslink konnte nicht erstellt werden**\n\n"
                    f"Fehler: {result}\n\n"
                    "Bitte versuche es später erneut oder wähle TWINT / Bargeld."
                )
                buttons = [[InlineKeyboardButton("Erneut versuchen", callback_data="pay|sumup")]]

            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown",
                disable_web_page_preview=False
            )

        else:
            context.user_data["zahlung"] = methode
            context.user_data["status"] = "awaiting_proof"
            buttons = [[InlineKeyboardButton("Bestellung abbrechen", callback_data="abbruch_bestellung")]]

            if methode == "twint":
                twint_link = generate_twint_link(gesamt_preis, bestellnr)
                text = (
                    "💳 **TWINT – Sichere Zahlung**\n\n"
                    f"Bestellnummer: `{bestellnr}`\n"
                    f"Gesamtbetrag: **{gesamt_preis:.2f} CHF**\n\n"
                    f"[Bezahle mit TWINT]({twint_link})\n\n"
                    "Der Betrag ist bereits korrekt vorausgefüllt.\n\n"
                    "Bitte sende **zuerst** den Screenshot deiner erfolgreichen Zahlung,\n"
                    "danach schreibe einfach „bezahlt“."
                )
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown",
                disable_web_page_preview=True
            )

    elif typ == "loeschen":
        _, index_str = data.split("|", 1)
        try:
            index = int(index_str)
        except ValueError:
            await query.edit_message_text("Fehler beim Löschen.")
            return
        warenkorb = context.user_data.get("warenkorb", [])
        if index < 0 or index >= len(warenkorb):
            await query.edit_message_text("Position nicht gefunden.")
            return
        entfernt = warenkorb.pop(index)
        await query.edit_message_text(f"Entfernt: {entfernt['menge']}× {entfernt['produkt']}")
        try:
            lager.erhoehen(entfernt['produkt'], entfernt['menge'])
        except Exception as e:
            print(f"Fehler beim Zurückzählen: {e}")
        await warenkorb_anzeigen(update, context)

    elif typ == "adresse_confirm":
        if value == "ja":
            context.user_data["confirmed_adresse"] = context.user_data.pop("temp_adresse", "")
            context.user_data["confirmed_whatsapp"] = context.user_data.pop("whatsapp", "")
            context.user_data["status"] = None
            warenkorb = context.user_data.get("warenkorb", [])
            gesamt_preis = sum(item["preis"] * item["menge"] for item in warenkorb)
            text = "Vielen Dank! Deine Adresse wurde gespeichert.\n\nWähle jetzt deine Versand- / Abhol-Option:"
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Standard-Versand (7 CHF)", callback_data="versand|standard")],
                    [InlineKeyboardButton("Selbstabholung (0 CHF)", callback_data="versand|selbstabholung")]
                ]),
                parse_mode="Markdown"
            )
        else:
            context.user_data["status"] = "awaiting_address"
            await query.edit_message_text(
                "Okay – bitte sende mir die korrekte Adresse + WhatsApp-Nummer noch einmal.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("← Zurück zum Warenkorb", callback_data="warenkorb")]
                ]),
                parse_mode="Markdown"
            )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if context.user_data.get("wartet_auf_menge"):
        try:
            menge = int(text)
            if menge <= 0:
                await update.message.reply_text("Bitte eine positive Anzahl angeben.")
                return
            produkt = context.user_data["aktuelles_produkt"]
            info = lager.holen(produkt)
            verfuegbar = info.get("menge", 0)
            if menge > verfuegbar:
                await update.message.reply_text(
                    f"Leider sind nur noch **{verfuegbar} Stück** verfügbar.\n"
                    "Wie viele möchtest du?"
                )
                return
            try:
                lager.reduzieren(produkt, menge)
            except Exception:
                await update.message.reply_text("❌ Lager konnte nicht reserviert werden.")
                return
            context.user_data["wartet_auf_menge"] = False
            warenkorb = context.user_data.setdefault("warenkorb", [])
            warenkorb.append({
                "produkt": produkt,
                "menge": menge,
                "preis": context.user_data["aktueller_preis"]
            })
            gesamt_preis = sum(item["preis"] * item["menge"] for item in warenkorb)
            await update.message.reply_text(
                f"**{menge}× {produkt}** wurde deinem Warenkorb hinzugefügt.\n\n"
                f"Gesamtpreis bisher: **{gesamt_preis:.2f} CHF**\n\n"
                "Möchtest du noch etwas hinzufügen?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Weiteres Produkt hinzufügen", callback_data="mehr_produkt|ja")],
                    [InlineKeyboardButton("🛒 Warenkorb anzeigen", callback_data="warenkorb")],
                    [InlineKeyboardButton("Zur Zahlung gehen", callback_data="adresse_abfrage")]
                ]),
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("Bitte nur eine Zahl eingeben.")
        return

    if context.user_data.get("status") == "awaiting_address":
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            await update.message.reply_text("Bitte Adresse und/oder WhatsApp-Nummer angeben.")
            return

        adresse = context.user_data.get("temp_adresse", "")
        whatsapp = context.user_data.get("whatsapp", "")

        neue_adresse_parts = []
        neue_nummer = None

        for line in lines:
            cleaned = line.replace(" ", "").replace("-", "").replace("/", "")
            if (
                (cleaned.startswith("+41") or cleaned.startswith("+49")) and len(cleaned) >= 11 and cleaned[1:].isdigit()
            ) or (
                (cleaned.startswith("0041") or cleaned.startswith("0049")) and len(cleaned) >= 12 and cleaned[2:].isdigit()
            ) or (
                (cleaned.startswith("07") or cleaned.startswith("015")) and len(cleaned) >= 10 and cleaned.isdigit()
            ):
                neue_nummer = line
            else:
                neue_adresse_parts.append(line)

        neue_adresse = "\n".join(neue_adresse_parts).strip()

        if neue_adresse:
            adresse = neue_adresse
        if neue_nummer:
            whatsapp = neue_nummer

        context.user_data["temp_adresse"] = adresse
        context.user_data["whatsapp"] = whatsapp

        if not adresse:
            await update.message.reply_text(
                "Bitte gib deine **Lieferadresse** an (Straße, PLZ, Ort).\n"
                "Du kannst die Nummer später nachschicken – ich merke mir, was du schon geschickt hast."
            )
            return

        if not whatsapp:
            await update.message.reply_text(
                "Danke für die Adresse!\n"
                "Jetzt brauche ich noch deine **WhatsApp-Nummer** (z. B. +41 76 123 45 67 oder 0761234567).\n"
                "Ich merke mir die Adresse – du musst sie nicht nochmal schicken."
            )
            return

        checking_msg = await update.message.reply_text(
            "Haben Sie bitte Geduld, wir überprüfen Ihre Adresse im System...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(5)

        query = "+".join(adresse.split())
        maps_url = f"https://www.google.com/maps/search/?api=1&query={query}"

        await update.message.reply_text(
            f"Ist das korrekt?\n\n"
            f"**Adresse:**\n{adresse}\n\n"
            f"**WhatsApp:** {whatsapp}\n\n"
            f"[In Google Maps anschauen]({maps_url})",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Ja – stimmt", callback_data="adresse_confirm|ja")],
                [InlineKeyboardButton("Nein – falsch", callback_data="adresse_confirm|nein")]
            ]),
            parse_mode="Markdown"
        )

        try:
            await checking_msg.delete()
        except:
            pass

        return

    await bezahlt_handler(update, context)

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
