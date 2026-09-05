import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
import yt_dlp


# -----------------------------
# Render health-check server
# -----------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    print(f"Health server listening on port {port}")
    server.serve_forever()


threading.Thread(target=run_health_server, daemon=True).start()


# -----------------------------
# Telegram Bot
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not configured")


bot = telebot.TeleBot(BOT_TOKEN)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@bot.message_handler(commands=["start", "help"])
def welcome(message):
    bot.reply_to(
        message,
        "👋 Welcome to the Video Downloader Bot!\n\n"
        "Send me a supported video URL and I'll try to download it for you."
    )


@bot.message_handler(
    func=lambda message: (
        bool(message.text)
        and message.text.strip().startswith(
            ("http://", "https://")
        )
    )
)
def download_video(message):
    url = message.text.strip()


    status = bot.reply_to(message, "⏳ Processing your link...")

    filename = None

    try:
        ydl_opts = {
            "format": "best[ext=mp4][filesize<50M]/best[filesize<50M]/best",
            "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        if not os.path.exists(filename):
            raise FileNotFoundError("Downloaded file was not found.")

        bot.edit_message_text(
            "📤 Download complete! Sending the video...",
            chat_id=message.chat.id,
            message_id=status.message_id,
        )

        with open(filename, "rb") as video:
            bot.send_video(message.chat.id, video)

        bot.delete_message(
            chat_id=message.chat.id,
            message_id=status.message_id,
        )

    except Exception as e:
        print(f"Download error: {type(e).__name__}: {e}")

        try:
            bot.edit_message_text(
                "❌ Sorry, I couldn't download that video.\n"
                "The link may be unsupported, private, unavailable, "
                "or the file may be too large.",
                chat_id=message.chat.id,
                message_id=status.message_id,
            )
        except Exception:
            pass

    finally:
        if filename and os.path.exists(filename):
            try:
                os.remove(filename)
            except Exception:
                pass


print("🤖 Telegram bot is running...")
bot.infinity_polling()
