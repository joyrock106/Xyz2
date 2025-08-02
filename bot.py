import telebot
import subprocess
import os
import re
import time

# 🔐 টোকেন বসাও (BotFather থেকে)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
bot = telebot.TeleBot(BOT_TOKEN)

# 📂 ডাউনলোড লোকেশন (Termux-এ)
DOWNLOAD_DIR = "/data/data/com.termux/files/home/storage/downloads"

# 🔠 ফাইলনেম স্যানিটাইজ
def generate_filename(url):
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    name = re.sub(r'\W+', '_', url)[:50]
    return f"{name}_{timestamp}.mp4"

# 🚀 স্টার্ট কমান্ড
@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "👋 Hi! Send me a .m3u8 link and I will record 1 minute of video for you.")

# 🧠 ইউজার ইনপুট হ্যান্ডলার
@bot.message_handler(func=lambda message: True)
def record_video(message):
    url = message.text.strip()

    if not url.startswith("http") or ".m3u8" not in url:
        bot.reply_to(message, "⚠️ Please send a valid .m3u8 link.")
        return

    filename = generate_filename(url)
    output_path = os.path.join(DOWNLOAD_DIR, filename)

    bot.reply_to(message, f"🎬 Recording started...\nSaving as: `{filename}`", parse_mode="Markdown")

    # 🎞️ FFmpeg রেকর্ডিং কমান্ড (1 মিনিট)
    cmd = f'ffmpeg -i "{url}" -c copy -t 00:01:00 "{output_path}"'

    try:
        subprocess.run(cmd, shell=True, check=True)
        bot.reply_to(message, f"✅ Done! Video saved as `{filename}` in Downloads.", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error while recording.\n{e}")

# 🤖 বট চালু রাখো
bot.polling()
