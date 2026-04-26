import os
import telebot
from flask import Flask, request
import requests
import json
from thefuzz import process, fuzz

# ================= CONFIG (From Environment Variables) =================
# Render ရဲ့ Dashboard > Environment မှာ သွားထည့်ပေးရမယ့် Key များ
BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

# Default ID များ (Environment မှာ မထည့်ထားရင် ဒီ ID တွေကို သုံးမယ်)
SOURCE_GROUP_ID = int(os.getenv("SOURCE_GROUP_ID", "-1003946938849"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "1774839794"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ================= HOME (For Monitoring) =================
@app.route("/", methods=["GET"])
def home():
    return "Bot is running on Webhook Mode", 200

# ================= WEBHOOK ROUTE =================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Invalid Request", 403

# ================= START COMMAND =================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "✅ Mflixer Movie Bot (Webhook Mode) အလုပ်လုပ်နေပါပြီ")

# ================= ADMIN POST (သိမ်းဆည်းရန်) =================
@bot.message_handler(content_types=['photo'])
def handle_admin_post(message):
    try:
        # Admin ID ကို စစ်ဆေးမယ်
        if message.from_user.id == ADMIN_ID and message.caption:
            title = message.caption.split('\n')[0]
            msg_id = message.message_id
            
            payload = {
                "key": SECRET_KEY,
                "action": "insert",
                "name": title,
                "id": msg_id
            }
            
            r = requests.post(GOOGLE_SCRIPT_URL, data=json.dumps(payload), timeout=25)
            if "Success" in r.text:
                bot.reply_to(message, f"✅ Saved: {title}")
            else:
                bot.reply_to(message, "❌ Database Error")
    except Exception as e:
        print(f"Insert error: {e}")

# ================= SEARCH (ရုပ်ရှင်ရှာရန်) =================
@bot.message_handler(func=lambda message: True)
def search_movie(message):
    try:
        payload = {"key": SECRET_KEY, "action": "search"}
        r = requests.post(GOOGLE_SCRIPT_URL, data=json.dumps(payload), timeout=25)
        data = r.json()
        
        movie_list = data[1:] if len(data) > 1 else []
        
        if not movie_list:
            bot.send_message(message.chat.id, "❌ Database ထဲမှာ ဘာမှမရှိသေးပါ")
            return

        names = [m[0] for m in movie_list]
        
        # Fuzzy matching နဲ့ ကိုက်ညီမှု ရှာမယ်
        results = process.extract(
            message.text, 
            names, 
            limit=3, 
            scorer=fuzz.partial_token_set_ratio
        )

        found = False
        for name, score in results:
            if score > 65: # ကိုက်ညီမှု 65% ကျော်ရင်
                target_id = next(m[1] for m in movie_list if m[0] == name)
                # Source Group ကနေ copy ကူးပို့ပေးမယ်
                bot.copy_message(message.chat.id, SOURCE_GROUP_ID, int(target_id))
                found = True
                break
        
        if not found:
            bot.send_message(message.chat.id, "🔍 ရှာမတွေ့ပါ၊ နာမည်ကို မှန်အောင် ပြန်ရိုက်ကြည့်ပါ")
            
    except Exception as e:
        print(f"Search error: {e}")
        bot.send_message(message.chat.id, "⚠️ Google Script နဲ့ ချိတ်ဆက်ရာမှာ အမှားရှိနေပါတယ်")

# ================= RUN =================
if __name__ == "__main__":
    # Render က PORT ကို အလိုအလျောက် သတ်မှတ်ပေးတာကို လက်ခံဖို့ဖြစ်ပါတယ်
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
