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
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8322086006:AAFF2-CuOWMNRcG3AYuhatKWSb5yVCOaFso')

# --- ២. FIREBASE SETUP ---
def get_firebase_key_path():
    # រកមើលក្នុង Folder ធម្មតា
    if os.path.exists("serviceAccountKey.json"):
        return "serviceAccountKey.json"
    # រកមើលក្នុង Secret Folder របស់ Render
    elif os.path.exists("/etc/secrets/serviceAccountKey.json"):
        return "/etc/secrets/serviceAccountKey.json"
    return None

key_path = get_firebase_key_path()

if key_path:
    try:
        cred = credentials.Certificate(key_path)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                # ជំនួស Link Database របស់អ្នកនៅទីនេះ
                'databaseURL': 'https://botdonwloadvideotk-default-rtdb.firebaseio.com/'
            })
        print(f"Firebase Connected using key at: {key_path}")
    except Exception as e:
        print(f"Firebase Init Error: {e}")
else:
    print("WARNING: Key not found. Database features will be disabled.")

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

# --- ៤. SAVE USER & HISTORY FUNCTIONS (Silent Mode) ---

def save_user_to_db(message):
    """ Save User info ស្ងាត់ៗ មិនប្រាប់ User ទេ """
    if not get_firebase_key_path(): return

    try:
        user_id = str(message.from_user.id)
        user_data = {
            'id': user_id,
            'first_name': message.from_user.first_name,
            'username': message.from_user.username if message.from_user.username else "None",
            'telegram_link': f"https://t.me/{message.from_user.username}" if message.from_user.username else "No Username",
            'last_active': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # ប្រើ update ដើម្បីកុំឱ្យបាត់ប្រវត្តិ history ចាស់
        ref = db.reference(f'users/{user_id}')
        ref.update(user_data)
        
        # Print ក្នុង Log របស់ Render ដើម្បីឱ្យ Admin ដឹង (User មិនឃើញទេ)
        print(f"Silent Save: User {message.from_user.first_name} updated.")
        
    except Exception as e:
        # បើ Error គ្រាន់តែ Print ទុកក្នុង Log មិនបាច់ប្រាប់ User
        print(f"Error saving user: {e}")

def save_download_history(message, video_url, video_title):
    """ Save History ស្ងាត់ៗ """
    if not get_firebase_key_path(): return

    try:
        user_id = str(message.from_user.id)
        
        history_data = {
            'url': video_url,
            'title': video_title,
            'downloaded_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # Save ចូលក្នុង Node "history"
        ref = db.reference(f'users/{user_id}/history')
        ref.push(history_data)
        print(f"Silent Save: History for {user_id} added.")

    except Exception as e:
        print(f"Error saving history: {e}")

# --- ៥. BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Save ស្ងាត់ៗ
    save_user_to_db(message)
    
    welcome_text = (
        f"សួស្តី <b>{message.from_user.first_name}</b>! 👋\n\n"
        "ផ្ញើ Link TikTok មកខ្ញុំ ខ្ញុំនឹង Download ជូនអ្នក។ 🚀"
    )
    bot.reply_to(message, welcome_text, parse_mode="HTML")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    text = message.text
    
    # Save User ស្ងាត់ៗ (ដើម្បី Update last_active)
    save_user_to_db(message)

    if "tiktok.com" in text:
        # សារជូនដំណឹងធម្មតា (លែងមានពាក្យថា Database ទៀតហើយ)
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
            
            # Save History ស្ងាត់ៗ
            save_download_history(message, text, title)

            # ផ្ញើវីដេអូ
            with open(filename, 'rb') as video:
                caption_text = f"🎬 <b>{title}</b>"
                bot.send_video(message.chat.id, video, caption=caption_text, parse_mode="HTML", reply_to_message_id=message.message_id)
            
            os.remove(filename)
            bot.delete_message(message.chat.id, status_msg.message_id)
            
        except Exception as e:
            bot.delete_message(message.chat.id, status_msg.message_id)
            bot.reply_to(message, f"❌ Download បរាជ័យ។\nError: {str(e)}")
            if 'filename' in locals() and os.path.exists(filename):
                os.remove(filename)
    else:
        bot.reply_to(message, "⚠️ សូមផ្ញើតែ Link TikTok ប៉ុណ្ណោះ។")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
