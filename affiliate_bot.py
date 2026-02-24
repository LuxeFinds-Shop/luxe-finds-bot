from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import json
import os
import asyncio
from datetime import datetime
import requests
from telegram.error import BadRequest
import random
import bcrypt  # pip install bcrypt

# ==================== CONFIG ====================
TOKEN = "8427022180:AAH40DCLb50kf-wRk-JU0kWcRNMU0dUY8EA"
SHOP_BOT_USERNAME = "LuxeFinds_Bot"
ADMINS = [6574712528, 6589321599]
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1466869469543530528/p38DSMKoMNJAG5m9YjMS1WZFvZfe5x6oFSjlI-rAKUUgZw6k8Z9f-jiDcOn4I0n_0JGx"
AFFILIATES_FILE = "affiliates.json"
PENDING_FILE = "pending_affiliates.json"
PROVISION_PER_VAPE = 3
MIN_AUSZAHLUNG = 10

# ==================== UTIL ====================
def lade_affiliates():
    if not os.path.exists(AFFILIATES_FILE):
        return {}
    try:
        with open(AFFILIATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def speichere_affiliates(data):
    with open(AFFILIATES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def lade_pending():
    if not os.path.exists(PENDING_FILE):
        return {}
    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def speichere_pending(data):
    with open(PENDING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def escape_md_v2(text: str) -> str:
    reserved = r'_*[]()~`>#+-=|{}.!'
    for c in reserved:
        text = text.replace(c, f'\\{c}')
    return text

# ==================== DISCORD ====================
def discord_embed_affiliate(user_id, name, status="NEUE ANFRAGE"):
    embed = {
        "title": "Affiliate Anfrage" if status == "NEUE ANFRAGE" else f"Affiliate {status}",
        "color": 0x9b59b6 if status == "NEUE ANFRAGE" else (0x2ecc71 if status == "BESTÄTIGT" else 0xe74c3c),
        "fields": [
            {"name": "User ID", "value": str(user_id), "inline": True},
            {"name": "Name", "value": name, "inline": True},
            {"name": "Status", "value": status, "inline": True},
        ],
        "footer": {"text": "LuxeFinds Affiliate " + datetime.now().strftime("%d.%m.%Y %H:%M")},
    }
    try:
        requests.post(DISCORD_WEBHOOK, json={"embeds": [embed]})
    except:
        pass

# ==================== GENERIEREN ====================
def generate_username_password(name: str):
    username = name.lower().replace(" ", "_") + str(random.randint(1000, 9999))
    password = str(random.randint(100000, 999999))
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    return username, password, hashed

# ==================== START ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    affiliates = lade_affiliates()
    pending = lade_pending()

    if user_id in affiliates:
        text = (
            "Willkommen zurück\n\n"
            "Wichtig! Solange du diesen Bot gestartet hast, bekommst du Provisions-Nachrichten privat\n"
            "Falls du nichts siehst, schreibe einfach nochmal /start\n\n"
            "Deine aktuellen Infos:"
        )
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        await mycode_cmd(update, context)
        return

    if user_id in pending:
        text = "Deine Anfrage wird noch geprüft. Bitte habe etwas Geduld (max. 5–10 Minuten)."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    text = "Willkommen beim LuxeFinds Affiliate Programm!\n\nBitte sende zuerst deinen vollständigen Namen."
    await update.message.reply_text(
        escape_md_v2(text),
        parse_mode="MarkdownV2"
    )
    context.user_data["awaiting_name"] = True

# ==================== TEXT HANDLER ====================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if context.user_data.get("awaiting_name"):
        name = update.message.text.strip()
        if not name or len(name.split()) < 2:
            text = "Bitte gib deinen vollständigen Namen an (Vor- und Nachname)."
            await update.message.reply_text(
                escape_md_v2(text),
                parse_mode="MarkdownV2"
            )
            return

        pending = lade_pending()
        pending[user_id] = {"name": name, "zeit": datetime.now().isoformat()}
        speichere_pending(pending)

        discord_embed_affiliate(user_id, name, status="NEUE ANFRAGE")

        text = f"Danke, {name}!\n\nDeine Anfrage wurde gesendet. Ein Admin prüft sie in Kürze.\nDu bekommst Bescheid, sobald du freigeschaltet bist."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        context.user_data["awaiting_name"] = False
        return

    text = "Unbekannter Befehl. Schreib /start oder warte auf Bestätigung."
    await update.message.reply_text(
        escape_md_v2(text),
        parse_mode="MarkdownV2"
    )

# ==================== /clearaffiliate ====================
async def clearaffiliate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        text = "Nur Admins können das machen."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    buttons = [
        [InlineKeyboardButton("Ja, wirklich ALLES löschen", callback_data="clear_confirm_yes")],
        [InlineKeyboardButton("Nein, abbrechen", callback_data="clear_confirm_no")]
    ]

    warn_text = (
        "⚠️ ACHTUNG ⚠️\n\n"
        "Das löscht ALLE Affiliates und ALLE wartenden Anfragen unwiderruflich!\n"
        "Egal ob bestätigt oder nicht.\n\n"
        "Bist du 100% sicher?"
    )

    await update.message.reply_text(
        escape_md_v2(warn_text),
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ==================== BUTTON HANDLER ====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "clear_confirm_yes":
        if os.path.exists(AFFILIATES_FILE):
            os.remove(AFFILIATES_FILE)
        if os.path.exists(PENDING_FILE):
            os.remove(PENDING_FILE)
        text = "Alle Affiliates und Pending-Anfragen wurden gelöscht."
        await query.edit_message_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
    elif query.data == "clear_confirm_no":
        text = "Aktion abgebrochen."
        await query.edit_message_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )

# ==================== /confirmaff ====================
async def confirmaff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        text = "Nutzung: /confirmaff USERID"
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    user_id = context.args[0]
    pending = lade_pending()

    if user_id not in pending:
        text = "Keine pending Anfrage für diese ID."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    name = pending[user_id]["name"]
    affiliates = lade_affiliates()

    if user_id in affiliates:
        text = "User hat bereits einen Account/Code."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    code = (name.upper().replace(" ", "")[:6] + str(random.randint(10, 99))).upper()
    link = f"https://t.me/{SHOP_BOT_USERNAME}?start={code}"

    username, plain_pw, hashed_pw = generate_username_password(name)

    affiliates[user_id] = {
        "name": name,
        "code": code,
        "link": link,
        "username": username,
        "hashed_pw": hashed_pw,
        "balance": 0.0
    }
    speichere_affiliates(affiliates)

    discord_embed_affiliate(user_id, name, status="BESTÄTIGT")

    success_text = (
        f"Deine Anfrage wurde bestätigt!\n\n"
        f"Dein Code: {code}\n\n"
        f"Login:\n"
        f"Username: {username}\n"
        f"Passwort: {plain_pw}\n\n"
        f"Provision: {PROVISION_PER_VAPE} CHF pro Vape\n"
        f"Min Auszahlung: {MIN_AUSZAHLUNG} CHF\n\n"
        "Logge dich ein mit: /login <username> <passwort>\n\n"
        "Dein Werbe-Link:"
    )

    buttons = [[InlineKeyboardButton("Deinen Affiliate-Link öffnen", url=link)]]

    try:
        await context.bot.send_message(
            user_id,
            escape_md_v2(success_text),
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    except BadRequest as e:
        await context.bot.send_message(
            user_id,
            success_text.replace('\\', ''),
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    pending.pop(user_id)
    speichere_pending(pending)

    text = f"Bestätigt: {user_id} ({name}) → Code: {code}"
    await update.message.reply_text(
        escape_md_v2(text),
        parse_mode="MarkdownV2"
    )

# ==================== /rejectaff ====================
async def rejectaff_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    if not context.args:
        text = "Nutzung: /rejectaff USERID"
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    user_id = context.args[0]
    pending = lade_pending()

    if user_id not in pending:
        text = "Keine pending Anfrage."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    name = pending[user_id]["name"]
    discord_embed_affiliate(user_id, name, status="ABGELEHNT")

    try:
        reject_text = (
            "Leider wurde deine Affiliate-Anfrage abgelehnt.\n"
            "Bei Fragen melde dich beim Support."
        )
        await context.bot.send_message(
            user_id,
            escape_md_v2(reject_text),
            parse_mode="MarkdownV2"
        )
    except:
        pass

    pending.pop(user_id)
    speichere_pending(pending)

    text = f"Abgelehnt: {user_id} ({name})"
    await update.message.reply_text(
        escape_md_v2(text),
        parse_mode="MarkdownV2"
    )

# ==================== /login ====================
async def login_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    affiliates = lade_affiliates()

    if user_id not in affiliates:
        text = "Du bist kein Affiliate. Starte mit /start."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    if len(context.args) != 2:
        text = "Nutzung: /login USERNAME PASSWORT"
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    input_user = context.args[0]
    input_pw = context.args[1]

    aff = affiliates[user_id]
    if aff.get("username") != input_user:
        text = "Falscher Username."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    if not bcrypt.checkpw(input_pw.encode('utf-8'), aff["hashed_pw"].encode('utf-8')):
        text = "Falsches Passwort."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    context.user_data["aff_logged_in"] = True
    context.user_data["aff_user_id"] = user_id

    text = (
        "Login erfolgreich!\n\n"
        "Du kannst jetzt deine Infos sehen:\n"
        "/mycode – deinen Link & Code\n"
        "/balance – aktueller Stand"
    )
    await update.message.reply_text(
        escape_md_v2(text),
        parse_mode="MarkdownV2"
    )

# ==================== /mycode ====================
async def mycode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    affiliates = lade_affiliates()

    if user_id not in affiliates:
        text = "Du bist kein Affiliate."
        await update.message.reply_text(
            escape_md_v2(text),
            parse_mode="MarkdownV2"
        )
        return

    aff = affiliates[user_id]
    text = (
        f"**Dein Affiliate-Account**\n\n"
        f"Name: {aff['name']}\n"
        f"Code: `{aff['code']}`\n"
        f"Link: {aff['link']}\n\n"
        f"Saldo: {aff.get('balance', 0.0):.2f} CHF"
    )

    await update.message.reply_text(
        escape_md_v2(text),
        parse_mode="MarkdownV2"
    )

# ==================== MAIN ====================
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clearaffiliate", clearaffiliate))
    app.add_handler(CommandHandler("confirmaff", confirmaff_cmd))
    app.add_handler(CommandHandler("rejectaff", rejectaff_cmd))
    app.add_handler(CommandHandler("login", login_cmd))
    app.add_handler(CommandHandler("mycode", mycode_cmd))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("LuxeFinds Affiliate Bot läuft – mit Login & Provision")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
