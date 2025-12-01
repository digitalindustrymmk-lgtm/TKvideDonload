import telebot
import yt_dlp
import os
import time
from flask import Flask
from threading import Thread

# --- CONFIGURATION ---
# ដាក់ Token ថ្មីរបស់អ្នកនៅទីនេះ (ឬប្រើ Environment Variable លើ Render)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8322086006:AAFScNAWiukoQlMChoBv8jW76qh380sl62g')

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask('')

# --- FLASK SERVER (ដើម្បីឱ្យ Render ដើររហូត) ---
@app.route('/')
def home():
    return "I am alive! The Bot is running."

def run_http():
    # Render ត្រូវការ Port នេះ
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- TIKTOK DOWNLOAD LOGIC ---
def download_video(url):
    ydl_opts = {
        'format': 'best',  # យកគុណភាពល្អបំផុត
        'outtmpl': 'video_%(id)s.%(ext)s', # ឈ្មោះ file
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename

# --- BOT HANDLERS ---
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "សួស្តី! ផ្ញើ Link TikTok មកខ្ញុំ ខ្ញុំនឹង Download ជូនអ្នកដោយគ្មាន Watermark។")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    text = message.text
    
    # ពិនិត្យមើលថាជា link TikTok ឬអត់
    if "tiktok.com" in text:
        msg = bot.reply_to(message, "កំពុងដំណើរការ... សូមរង់ចាំបន្តិច ⏳")
        
        try:
            # ទាញយកវីដេអូ
            video_path = download_video(text)
            
            # ផ្ញើវីដេអូទៅកាន់អ្នកប្រើប្រាស់
            with open(video_path, 'rb') as video:
                bot.send_video(message.chat.id, video, caption="នេះគឺជាវីដេអូរបស់អ្នក! \nទាញយកដោយ: @YourBotName", reply_to_message_id=message.message_id)
            
            # លុប file ចេញពី Server ដើម្បីកុំឱ្យពេញ Space
            os.remove(video_path)
            bot.delete_message(message.chat.id, msg.message_id) # លុបសារ "កំពុងដំណើរការ"
            
        except Exception as e:
            bot.reply_to(message, f"មានបញ្ហាក្នុងការទាញយក។ សូមព្យាយាមម្តងទៀត។\nError: {e}")
            if 'video_path' in locals() and os.path.exists(video_path):
                os.remove(video_path)
    else:
        bot.reply_to(message, "សូមផ្ញើតែ Link TikTok ប៉ុណ្ណោះ។")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    keep_alive() # បើក Web Server
    bot.infinity_polling() # បើក Bot
