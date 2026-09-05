import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import telebot
from telebot import types
import yt_dlp
import imageio_ffmpeg


# =========================
# Render health-check server
# =========================

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


threading.Thread(
    target=run_health_server,
    daemon=True
).start()


# =========================
# Telegram bot
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not configured")

bot = telebot.TeleBot(BOT_TOKEN)


# Store URLs temporarily for each user
user_urls = {}


@bot.message_handler(commands=["start"])
def start_command(message):
    bot.reply_to(
        message,
        "👋 Welcome!\n\n"
        "🔗 Send me a video URL and I'll download it for you."
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.reply_to(
        message,
        "ℹ️ Send a supported video URL to download it."
    )


# =========================
# Receive video URL
# =========================

@bot.message_handler(
    func=lambda message: (
        bool(message.text)
        and message.text.strip().startswith(
            ("http://", "https://")
        )
    )
)
def receive_url(message):

    url = message.text.strip()

    # Save URL for this user
    user_urls[message.from_user.id] = url

    markup = types.InlineKeyboardMarkup()

    sound_button = types.InlineKeyboardButton(
        "🎵 With Sound",
        callback_data="with_sound"
    )

    silent_button = types.InlineKeyboardButton(
        "🔇 Without Sound",
        callback_data="without_sound"
    )

    markup.add(sound_button, silent_button)

    bot.reply_to(
        message,
        "🎬 Video link received!\n\n"
        "Choose how you want to download it:",
        reply_markup=markup
    )


# =========================
# Button handling
# =========================

@bot.callback_query_handler(
    func=lambda call: call.data in [
        "with_sound",
        "without_sound"
    ]
)
def handle_download_choice(call):

    user_id = call.from_user.id

    if user_id not in user_urls:
        bot.answer_callback_query(
            call.id,
            "❌ Link expired. Please send the URL again."
        )
        return

    url = user_urls[user_id]

    if call.data == "with_sound":
        with_sound = True
        choice_text = "🎵 With Sound"
    else:
        with_sound = False
        choice_text = "🔇 Without Sound"

    bot.answer_callback_query(
        call.id,
        f"Selected: {choice_text}"
    )

    status_message = bot.send_message(
        call.message.chat.id,
        f"⏳ Downloading...\n\n{choice_text}"
    )

    filename = None

    try:

        os.makedirs("downloads", exist_ok=True)

        if with_sound:

            ydl_opts = {
                "format": "bestvideo+bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "merge_output_format": "mp4",
                "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
                "noplaylist": True,
                "quiet": True,
            }

        else:

            # Download video-only stream
            ydl_opts = {
                "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "noplaylist": True,
                "quiet": True,
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

            filename = ydl.prepare_filename(info)

            # When yt-dlp merges into MP4, extension may change
            if with_sound:

                possible_mp4 = os.path.splitext(filename)[0] + ".mp4"

                if os.path.exists(possible_mp4):
                    filename = possible_mp4

        if not filename or not os.path.exists(filename):
            raise FileNotFoundError(
                "Downloaded video file not found."
            )

        bot.edit_message_text(
            "📤 Download complete!\n\n"
            "Sending video...",
            chat_id=status_message.chat.id,
            message_id=status_message.message_id
        )

        with open(filename, "rb") as video_file:

            bot.send_video(
                call.message.chat.id,
                video_file,
                supports_streaming=True
            )

        bot.delete_message(
            chat_id=status_message.chat.id,
            message_id=status_message.message_id
        )

    except Exception as e:

        print(
            f"Download error: {type(e).__name__}: {e}"
        )

        try:

            bot.edit_message_text(
                "❌ Sorry, I couldn't download this video.\n\n"
                "Please try another link.",
                chat_id=status_message.chat.id,
                message_id=status_message.message_id
            )

        except Exception:
            pass

    finally:

        if filename and os.path.exists(filename):

            try:
                os.remove(filename)
            except Exception:
                pass

        # Remove saved URL
        user_urls.pop(user_id, None)


# =========================
# Start bot
# =========================

print("🤖 Telegram bot is running...")

bot.infinity_polling(
    skip_pending=True
)
