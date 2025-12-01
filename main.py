import telebot
import yt_dlp
import os
import time
from flask import Flask
from threading import Thread
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8322086006:AAFScNAWiukoQlMChoBv8jW76qh380sl62g')

# --- FIREBASE SETUP ---
# ត្រូវប្រាកដថាអ្នកបានដាក់ file 'serviceAccountKey.json' ចូលក្នុង GitHub ឬ Render
# ហើយកុំភ្លេចប្តូរ 'https://YOUR-PROJECT-ID.firebaseio.com/' ទៅជា Link Database របស់អ្នក
cred = credentials.Certificate("serviceAccountKey.json")

# ចំណាំ៖ កន្លែង databaseURL ត្រូវដាក់ Link Realtime Database របស់អ្នក
# អ្នកអាចរកវាបាននៅផ្នែក Realtime Database ក្នុង Firebase Console
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://botdonwloadvideotk-default-rtdb.firebaseio.com/' 
}) 
# (ខាងលើជាឧទាហរណ៍ Link ខ្ញុំ សូមដូរដាក់របស់អ្នក។ Link របស់អ្នកចប់ដោយ .firebasedatabase.app)

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# --- FLASK SERVER ---
@app.route('/')
def home():
    return "Bot is running with Firebase!"

def run_http():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- SAVE USER TO FIREBASE ---
def save_user_to_db(message):
    try:
        user_id = str(message.from_user.id)
        first_name = message.from_user.first_name
        username = message.from_user.username
        
        # បង្កើត Telegram Link
        if username:
            telegram_link = f"https://t.me/{username}"
        else:
            telegram_link = "No Username"

        # ទិន្នន័យដែលត្រូវរក្សាទុក
        user_data = {
            'id': user_id,
            'first_name': first_name,
            'username': username if username else "None",
            'telegram_link': telegram_link,
            'joined_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        # សរសេរចូល Database (Path: users/USER_ID)
        ref = db.reference(f'users/{user_id}')
        ref.set(user_data)
        print(f"Saved user: {first_name}")
        
    except Exception as e:
        print(f"Error saving to Firebase: {e}")

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # ១. រក្សាទុកទិន្នន័យ User ចូល Firebase ភ្លាមៗ
    save_user_to_db(message)
    
    # ២. ឆ្លើយតបទៅ User វិញ
    bot.reply_to(message, f"សួស្តី {message.from_user.first_name}! 👋\nផ្ញើ Link TikTok មកខ្ញុំ ខ្ញុំនឹង Download ជូនអ្នកដោយគ្មាន Watermark។")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    text = message.text
    
    # បើក User មិនទាន់ចុច Start តែផ្ញើ Link មកក៏យើងអាច Save បានដែរ (Optional)
    # save_user_to_db(message) 

    if "tiktok.com" in text:
        msg = bot.reply_to(message, "កំពុងដំណើរការ... ⏳")
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': 'video_%(id)s.%(ext)s',
                'quiet': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(text, download=True)
                filename = ydl.prepare_filename(info)
            
            with open(filename, 'rb') as video:
                bot.send_video(message.chat.id, video, caption="សម្រេច! \n@YourBotName")
            
            os.remove(filename)
            bot.delete_message(message.chat.id, msg.message_id)
            
        except Exception as e:
            bot.reply_to(message, "Error downloading.")
            if 'filename' in locals() and os.path.exists(filename):
                os.remove(filename)
    else:
        bot.reply_to(message, "សូមផ្ញើ Link TikTok តែប៉ុណ្ណោះ យើងនិង Download video សម្រាប់អ្នក។")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
