import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot


# -----------------------------
# Render health-check server
# -----------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Telegram bot is running!")

    def log_message(self, format, *args):
        pass


def run_health_server():
    port = int(os.environ.get("PORT", 10000))

    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)

    print(f"Health server running on port {port}")

    server.serve_forever()


# Start health server in background
threading.Thread(
    target=run_health_server,
    daemon=True
).start()


# -----------------------------
# Telegram Bot
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")


bot = telebot.TeleBot(BOT_TOKEN)


@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(
        message,
        "👋 Welcome!\n\n"
        "Your bot is working successfully! ✅"
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.reply_to(
        message,
        "ℹ️ Send /start to begin."
    )


print("🤖 Telegram bot is running...")

bot.infinity_polling()
