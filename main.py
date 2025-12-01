import telebot
import yt_dlp
import os
import time
from flask import Flask
from threading import Thread
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# --- ១. CONFIGURATION (កំណត់ការកំណត់) ---
# អ្នកអាចដាក់ Token ផ្ទាល់នៅទីនេះ ឬដាក់ក្នុង Render Environment Variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8322086006:AAFScNAWiukoQlMChoBv8jW76qh380sl62g')

# --- ២. FIREBASE SETUP (កំណត់ទិន្នន័យ) ---
# ពិនិត្យមើលថាតើមាន file key ដែរឬទេ
if os.path.exists("serviceAccountKey.json"):
    cred = credentials.Certificate("serviceAccountKey.json")
    
    # ចំណាំ: ខ្ញុំបានដាក់ Link តាមរូបភាពដែលអ្នកផ្ញើមក
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://botdonwloadvideotk-default-rtdb.firebaseio.com/'
            })
        print("Firebase Connected!")
    except Exception as e:
        print(f"Firebase Init Error: {e}")
else:
    print("WARNING: 'serviceAccountKey.json' not found! Database will not work.")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# --- ៣. FLASK SERVER (Keep Alive) ---
@app.route('/')
def home():
    return "Bot is running..."

def run_http():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- ៤. SAVE USER FUNCTION (រក្សាទុកទិន្នន័យ) ---
def save_user_to_db(message):
    # ពិនិត្យមើលថាមាន Key អត់?
    if not os.path.exists("serviceAccountKey.json"):
        bot.reply_to(message, "⚠️ <b>Admin Warning:</b> រកមិនឃើញ file <code>serviceAccountKey.json</code> ទេ។ សូម Upload វាចូល GitHub ឬ Render Secret Files ជាមុនសិន។", parse_mode="HTML")
        return

    try:
        user_id = str(message.from_user.id)
        first_name = message.from_user.first_name
        username = message.from_user.username
        
        # បង្កើត Link Telegram
        if username:
            telegram_link = f"https://t.me/{username}"
        else:
            telegram_link = "No Username"

        user_data = {
            'id': user_id,
            'first_name': first_name,
            'username': username if username else "None",
            'telegram_link': telegram_link,
            'joined_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'last_active': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # សរសេរចូល Database (Path: users/USER_ID)
        ref = db.reference(f'users/{user_id}')
        ref.set(user_data)
        
        # ផ្ញើសារប្រាប់ថាជោគជ័យ (Testing only - អាចលុបវិញពេលក្រោយ)
        # bot.reply_to(message, "✅ ទិន្នន័យរបស់អ្នកត្រូវបាន Save ចូល Database ជោគជ័យ!")
        print(f"Saved user: {first_name}")
        
    except Exception as e:
        # បង្ហាញកំហុសទៅ Admin តាមរយៈ Chat តែម្តង
        bot.reply_to(message, f"❌ <b>Database Error:</b>\n<code>{str(e)}</code>", parse_mode="HTML")

# --- ៥. BOT HANDLERS (ការឆ្លើយតប) ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # រក្សាទុក User ចូល Firebase
    save_user_to_db(message)
    
    welcome_text = (
        f"សួស្តី <b>{message.from_user.first_name}</b>! 👋\n\n"
        "ខ្ញុំគឺជា Bot សម្រាប់ Download វីដេអូ TikTok ដោយគ្មាន Watermark។\n"
        "គ្រាន់តែផ្ញើ Link TikTok មកខ្ញុំ ខ្ញុំនឹងធ្វើការជូនអ្នកភ្លាមៗ! 🚀"
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    text = message.text
    
    # Update last active time (Optional)
    # save_user_to_db(message) 

    if "tiktok.com" in text:
        status_msg = bot.reply_to(message, "⏳ កំពុងដំណើរការ... សូមរង់ចាំបន្តិច...")
        
        try:
            # ការកំណត់ Download
            ydl_opts = {
                'format': 'best',
                'outtmpl': 'video_%(id)s.%(ext)s',
                'quiet': True,
                'no_warnings': True
            }
            
            # ចាប់ផ្តើម Download
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)
                title = info.get('title', 'TikTok Video')
            
            # ផ្ញើវីដេអូ
            with open(filename, 'rb') as video:
                caption_text = f"🎬 <b>{title}</b>\n\n✅ Downloaded by @YourBotName"
                bot.send_video(message.chat.id, video, caption=caption_text, parse_mode="HTML", reply_to_message_id=message.message_id)
            
            # លុប file ចោល
            os.remove(filename)
            bot.delete_message(message.chat.id, status_msg.message_id)
            
        except Exception as e:
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.reply_to(message, f"❌ មានបញ្ហាក្នុងការ Download។\nError: {str(e)}")
            # Clean up if file exists
            if 'filename' in locals() and os.path.exists(filename):
                os.remove(filename)
    else:
        bot.reply_to(message, "⚠️ សូមផ្ញើតែ Link TikTok ប៉ុណ្ណោះ។")

# --- ៦. MAIN EXECUTION ---
if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
