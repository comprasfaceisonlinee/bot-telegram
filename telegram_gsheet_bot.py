
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
import asyncio
import os
import json
import time
import threading
from flask import Flask

# --- Configurações (Preencha com suas informações) ---
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID_STR = os.environ.get("TELEGRAM_CHANNEL_ID")

# Se você não definir essas variáveis no Render, o bot usará esses nomes padrão:
GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME", "Planilha Promocoes")
WORKSHEET_NAME = os.environ.get("WORKSHEET_NAME", "Página1")

GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", 3600))

# --- Funções do Bot ---

async def send_telegram_message(bot_token, chat_id, message_text, image_url=None):
    bot = Bot(token=bot_token)
    try:
        if image_url and str(image_url).startswith('http'):
            await bot.send_photo(chat_id=chat_id, photo=image_url, caption=message_text, parse_mode='HTML')
        else:
            await bot.send_message(chat_id=chat_id, text=message_text, parse_mode='HTML')
        print(f"✅ Mensagem enviada com sucesso para {chat_id}")
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem para {chat_id}: {e}")

def get_sheet_data(sheet_name, worksheet_name, credentials_json):
    try:
        print(f"🔍 Tentando acessar a planilha: '{sheet_name}' na aba: '{worksheet_name}'...")
        creds_dict = json.loads(credentials_json)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        print(f"❌ Erro ao obter dados da planilha: {e}")
        return []

async def process_offers():
    print("\n--- Iniciando nova verificação de ofertas ---")

    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID_STR, GOOGLE_CREDENTIALS_JSON]):
        print("❌ ERRO: Variáveis de ambiente faltando no Render!")
        return

    try:
        channel_id = int(TELEGRAM_CHANNEL_ID_STR.strip())
    except Exception:
        print(f"❌ ERRO: ID do Canal inválido: '{TELEGRAM_CHANNEL_ID_STR}'")
        return

    offers = get_sheet_data(GOOGLE_SHEET_NAME, WORKSHEET_NAME, GOOGLE_CREDENTIALS_JSON)

    if not offers:
        print("⚠️ Nenhuma oferta encontrada ou erro de acesso.")
        return

    print(f"📦 Encontradas {len(offers)} linhas na planilha.")

    for i, offer in enumerate(offers, 1):
        offer_text = offer.get('Texto da Oferta')
        product_link = offer.get('Link do Produto')
        image_url = offer.get('Imagem')

        if not offer_text or not product_link:
            print(f"⏭️ Pulando linha {i+1}: Texto ou Link faltando.")
            continue

        message = f"<b>{offer_text}</b>\n\n🛒 <a href=\"{product_link}\">PEGUE A OFERTA AQUI!</a>\n\n#oferta #achadinhos #promoção"

        await send_telegram_message(TELEGRAM_BOT_TOKEN, channel_id, message, image_url)
        time.sleep(3) 

    print("--- Fim do processamento ---\n")

async def bot_loop():
    while True:
        await process_offers()
        print(f"💤 Aguardando {CHECK_INTERVAL_SECONDS / 60} minutos...")
        time.sleep(CHECK_INTERVAL_SECONDS)

# --- Web Server para o Render ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Ativo!", 200

def run_flask_app():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

async def main():
    threading.Thread(target=run_flask_app, daemon=True).start()
    await bot_loop()

if __name__ == '__main__':
    asyncio.run(main())
