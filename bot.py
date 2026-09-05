import os
import telebot
import yt_dlp

# 1. Paste your Telegram Bot Token from BotFather here
BOT_TOKEN = "8863166130:AAELe3mzAuFosVFJN0d78BLwOvfAloAbB8Y"
bot = telebot.TeleBot(BOT_TOKEN)

# Directory to temporarily hold downloading videos
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome! Just send me a video link from YouTube, TikTok, or Instagram, and I will download it for you.")

@bot.message_handler(func=lambda message: True)
def download_and_send_video(message):
    url = message.text.strip()
    
    # Check if the message looks like a link
    if not url.startswith(("http://", "https://")):
        bot.reply_to(message, "❌ Please send a valid video URL link.")
        return

    status_message = bot.reply_to(message, "⏳ Processing your link... Please wait.")

    # Configure yt-dlp options (Limits to 720p/360p or under so Telegram can upload it easily)
    ydl_opts = {
        'format': 'best[ext=mp4][filesize<50M]/best', # Telegram limits free bots to 50MB files
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info and download the video file
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        # Send the file back to the user on Telegram
        bot.edit_message_text("📤 Downloading complete! Sending video file...", chat_id=message.chat.id, message_id=status_message.message_id)
        
        with open(filename, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)
            
        # Delete the file from your server after sending to save space
        os.remove(filename)
        bot.delete_message(chat_id=message.chat.id, message_id=status_message.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Failed to download video. The link might be broken or private.", chat_id=message.chat.id, message_id=status_message.message_id)
        # Clean up file if it exists but crashed mid-way
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)

print("Bot is successfully running...")
bot.infinity_polling()