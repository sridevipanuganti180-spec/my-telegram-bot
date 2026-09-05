import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
import yt_dlp

# 🌟 TRICK FOR RENDER FREE TIER: Simple web server to pass the port scan check
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_health_check_server():
    # Render automatically tells the bot what port to listen to using os.environ
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health check server successfully listening on port {port}")
    server.serve_forever()

# Start the fake web server in the background before starting the bot
threading.Thread(target=run_health_check_server, daemon=True).start()


# 🤖 2. YOUR ORIGINAL TELEGRAM BOT LOGIC
BOT_TOKEN = "8863166130:AAEoBqFLz54gHfzeBuGIFUFx7GTHFUxKWnA"  # <-- Put your token back here!
bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "👋 Welcome! Just send me a video link from YouTube, TikTok, or Instagram, and I will download it for you.")

@bot.message_handler(func=lambda message: True)
def download_and_send_video(message):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        bot.reply_to(message, "❌ Please send a valid video URL link.")
        return

    status_message = bot.reply_to(message, "⏳ Processing your link... Please wait.")

    ydl_opts = {
        'format': 'best[ext=mp4][filesize<50M]/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
        bot.edit_message_text("📤 Downloading complete! Sending video file...", chat_id=message.chat.id, message_id=status_message.message_id)
        
        with open(filename, 'rb') as video_file:
            bot.send_video(message.chat.id, video_file)
            
        os.remove(filename)
        bot.delete_message(chat_id=message.chat.id, message_id=status_message.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ Failed to download video. The link might be broken or private.", chat_id=message.chat.id, message_id=status_message.message_id)
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)

print("Bot is successfully running...")
bot.infinity_polling()
