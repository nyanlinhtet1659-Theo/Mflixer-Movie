import telebot
from flask import Flask, request
import requests
import json
from thefuzz import process, fuzz
import time

# ================= CONFIG =================
BOT_TOKEN = "8756073920:AAHLxNUimw-8uyjGFUs2HakKQ7NqdGYWeiI"
# သင့် Space URL ကို ဒီမှာ အမှန်ထည့်ပါ (ဥပမာ https://theo-mflixer.hf.space)
# အဆုံးမှာ / မပါစေနဲ့
SPACE_URL = "https://theo139-mflixer-movie.hf.space" 

GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyrA8Vlul_hED8hjCr88ulet-MzxOqWQrU2MwDLhJsKN6nP--1dOC1vM8ChNo63TDa1lg/exec"
SECRET_KEY = "Mflixer_Secret_99"
SOURCE_GROUP_ID = -1003946938849
ADMIN_ID = 1774839794

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= HOME & WEBHOOK SETTER =================
@app.route("/", methods=["GET"])
def home():
    # ဒီ Route ကို Browser မှာ ဖွင့်လိုက်တာနဲ့ Webhook ကို အလိုအလျောက် ချိတ်ပေးမယ်
    webhook_url = f"{SPACE_URL}/{BOT_TOKEN}/Webhook"
    bot.remove_webhook()
    time.sleep(1)
    success = bot.set_webhook(url=webhook_url)
    if success:
        return f"✅ Webhook Set Successfully! <br> URL: {webhook_url}", 200
    else:
        return "❌ Webhook Set Failed!", 500

# ================= WEBHOOK RECEIVER =================
@app.route(f"/{BOT_TOKEN}/Webhook", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# ================= START COMMAND =================
@bot.message_handler(commands=['start'])
def start(message):
    try:
        args = message.text.split()
        if len(args) > 1 and args[1].isdigit():
            bot.copy_message(message.chat.id, SOURCE_GROUP_ID, int(args[1]))
            return
        bot.reply_to(message, "✅ Mflixer Movie Bot is running!\n\nစာရိုက်ပြီး ဇာတ်ကားရှာနိုင်ပါပြီ 🎬")
    except Exception as e:
        print(f"Start error: {e}")

# ================= SEARCH LOGIC =================
@bot.message_handler(func=lambda message: True)
def search_movie(message):
    try:
        # နံပါတ်သက်သက် ရိုက်ရင် တိုက်ရိုက်ပို့မယ်
        if message.text.isdigit():
            bot.copy_message(message.chat.id, SOURCE_GROUP_ID, int(message.text))
            return

        # Google Sheets ကနေ Data ယူမယ်
        payload = {"key": SECRET_KEY, "action": "search"}
        r = requests.post(GOOGLE_SCRIPT_URL, data=json.dumps(payload), timeout=20)
        data = r.json()
        movie_list = data[1:] if len(data) > 1 else []
        
        if not movie_list:
            bot.send_message(message.chat.id, "❌ Database ထဲမှာ အချက်အလက် မရှိပါ။")
            return

        names = [m[0] for m in movie_list]
        results = process.extract(message.text, names, limit=3, scorer=fuzz.partial_token_set_ratio)

        for name, score in results:
            if score > 65:
                target_id = next(m[1] for m in movie_list if m[0] == name)
                bot.copy_message(message.chat.id, SOURCE_GROUP_ID, int(target_id))
                return
        
        bot.send_message(message.chat.id, "🔍 ရှာမတွေ့ပါ။ နာမည် အမှန်ပြန်ရိုက်ပေးပါ။")
    except Exception as e:
        print(f"Search error: {e}")

if __name__ == "__main__":
    # Hugging Face ရဲ့ Default Port 7860 မှာ Run မယ်
    app.run(host="0.0.0.0", port=7860)