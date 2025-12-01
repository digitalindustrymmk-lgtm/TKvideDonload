import telebot
import yt_dlp
import os
import time
from flask import Flask
from threading import Thread
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# --- ១. CONFIGURATION ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8322086006:AAFScNAWiukoQlMChoBv8jW76qh380sl62g')

# --- ២. FIREBASE SETUP (កែសម្រួលថ្មី) ---
# យើងបង្កើតមុខងារដើម្បីស្វែងរក Key ទាំងក្នុង Folder ធម្មតា និងក្នុង Secret Folder របស់ Render
def get_firebase_key_path():
    # ជម្រើសទី ១: រកមើលក្នុង Folder ធម្មតា (សម្រាប់ពេល test លើកុំព្យូទ័រ)
    if os.path.exists("serviceAccountKey.json"):
        return "serviceAccountKey.json"
    
    # ជម្រើសទី ២: រកមើលក្នុង Secret Folder របស់ Render (កន្លែងដែលអ្នកទើបតែដាក់)
    elif os.path.exists("/etc/secrets/serviceAccountKey.json"):
        return "/etc/secrets/serviceAccountKey.json"
    
    return None

key_path = get_firebase_key_path()

if key_path:
    try:
        cred = credentials.Certificate(key_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                # ត្រូវប្រាកដថា Link នេះត្រូវនឹង Firebase របស់អ្នក
                'databaseURL': 'https://botdonwloadvideotk-default-rtdb.firebaseio.com/'
            })
        print(f"Firebase Connected using key at: {key_path}")
    except Exception as e:
        print(f"Firebase Init Error: {e}")
else:
    print("WARNING: Key not found in root or /etc/secrets/")

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# --- ៣. FLASK SERVER ---
@app.route('/')
def home():
    return "Bot is running..."

def run_http():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- ៤. SAVE USER FUNCTION ---
def save_user_to_db(message):
    # ហៅមុខងារស្វែងរក Key ម្តងទៀត
    current_key_path = get_firebase_key_path()
    
    if not current_key_path:
        bot.reply_to(message, "⚠️ <b>Admin Warning:</b> រកមិនឃើញ file <code>serviceAccountKey.json</code> ទេ។ \nRender Path Checked: <code>/etc/secrets/serviceAccountKey.json</code>", parse_mode="HTML")
        return

    try:
        user_id = str(message.from_user.id)
        first_name = message.from_user.first_name
        username = message.from_user.username
        
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

        ref = db.reference(f'users/{user_id}')
        ref.set(user_data)
        print(f"Saved user: {first_name}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ <b>Database Error:</b>\n<code>{str(e)}</code>", parse_mode="HTML")

# --- ៥. BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
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
    
    if "tiktok.com" in text:
        status_msg = bot.reply_to(message, "⏳ កំពុងដំណើរការ... សូមរង់ចាំបន្តិច...")
        
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': 'video_%(id)s.%(ext)s',
                'quiet': True,
                'no_warnings': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)
                title = info.get('title', 'TikTok Video')
            
            with open(filename, 'rb') as video:
                caption_text = f"🎬 <b>{title}</b>"
                bot.send_video(message.chat.id, video, caption=caption_text, parse_mode="HTML", reply_to_message_id=message.message_id)
            
            os.remove(filename)
            bot.delete_message(message.chat.id, status_msg.message_id)
            
        except Exception as e:
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.reply_to(message, f"❌ មានបញ្ហាក្នុងការ Download។\nError: {str(e)}")
            if 'filename' in locals() and os.path.exists(filename):
                os.remove(filename)
    else:
        bot.reply_to(message, "⚠️ សូមផ្ញើតែ Link TikTok ប៉ុណ្ណោះ។")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
