import os
import subprocess
import datetime
import telebot
from telebot.types import Message
import json
import time
import logging

# ===================== CONFIG =====================
BOT_TOKEN = "8235565518:AAHTb-rqnxJzQ3KEuY8-livc8L1tydgnO2k"
DOWNLOAD_DIR = "./downloads"
WATERMARK = "@Nanette105"

# Telebot init with timeout for slow network
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
bot.timeout = 60  # Increase Telegram request timeout

# ===================== ADMIN / BLOCK SYSTEM =====================
ADMINS_FILE = 'admins.json'
BLOCKED_USERS_FILE = 'blocked.json'

# Load admins
if os.path.exists(ADMINS_FILE):
    with open(ADMINS_FILE, 'r') as f:
        ADMINS = json.load(f)
else:
    ADMINS = [1686274364]  # Your Admin ID
    with open(ADMINS_FILE, 'w') as f:
        json.dump(ADMINS, f)

# Load blocked users
if os.path.exists(BLOCKED_USERS_FILE):
    with open(BLOCKED_USERS_FILE, 'r') as f:
        BLOCKED_USERS = set(json.load(f))
else:
    BLOCKED_USERS = set()

def save_admins():
    with open(ADMINS_FILE, 'w') as f:
        json.dump(ADMINS, f)

def save_blocked():
    with open(BLOCKED_USERS_FILE, 'w') as f:
        json.dump(list(BLOCKED_USERS), f)

def is_admin(user_id):
    return user_id in ADMINS

def is_blocked(user_id):
    return user_id in BLOCKED_USERS

# ===================== HELPERS =====================
def sanitize_filename(name: str) -> str:
    return "".join(c for c in name if c.isalnum() or c in ('_', '-'))[:50]

def get_best_video_index(url: str) -> int:
    """Pick highest resolution video stream using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-select_streams", "v",
            "-show_entries", "stream=index,width,height",
            "-of", "json", url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return 0
        best = max(streams, key=lambda s: int(s.get("width", 0)) * int(s.get("height", 0)))
        return best["index"]
    except Exception as e:
        logging.error(f"ffprobe failed: {e}")
        return 0

# ===================== COMMANDS =====================
@bot.message_handler(commands=['start'])
def start_handler(message: Message):
    bot.send_message(message.chat.id,
        "🎬 Welcome to M3U8 Recorder Bot!\n\n"
        "To record:\n/rec [m3u8_link] [duration_seconds] [filename]\n\n"
        "Admin commands:\n"
        "/addadmin [user_id] - Add new admin\n"
        "/removeadmin [user_id] - Remove admin\n"
        "/block [user_id] - Block a user\n"
        "/unblock [user_id] - Unblock a user\n"
        "/id - Show your user ID"
    )

@bot.message_handler(commands=['id'])
def id_handler(message: Message):
    bot.reply_to(message, f"🆔 Your user ID: `{message.from_user.id}`", parse_mode="Markdown")

# ========== Admin Management ==========
@bot.message_handler(commands=['addadmin'])
def add_admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Only admins can add new admins.")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage:\n`/addadmin [user_id]`", parse_mode="Markdown")
        return
    try:
        new_admin_id = int(args[1])
    except:
        bot.reply_to(message, "❌ User ID must be an integer.")
        return
    if new_admin_id in ADMINS:
        bot.reply_to(message, "ℹ️ This user is already an admin.")
        return
    ADMINS.append(new_admin_id)
    save_admins()
    bot.reply_to(message, f"✅ {new_admin_id} has been added as admin.")

@bot.message_handler(commands=['removeadmin'])
def remove_admin_handler(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Only admins can remove admins.")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage:\n`/removeadmin [user_id]`", parse_mode="Markdown")
        return
    try:
        remove_id = int(args[1])
    except:
        bot.reply_to(message, "❌ User ID must be an integer.")
        return
    if remove_id not in ADMINS:
        bot.reply_to(message, "ℹ️ This user is not an admin.")
        return
    ADMINS.remove(remove_id)
    save_admins()
    bot.reply_to(message, f"✅ {remove_id} has been removed from admins.")

# ========== Block Management ==========
@bot.message_handler(commands=['block'])
def block_handler(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Only admins can block users.")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage:\n`/block [user_id]`", parse_mode="Markdown")
        return
    try:
        user_id = int(args[1])
    except:
        bot.reply_to(message, "❌ User ID must be an integer.")
        return
    BLOCKED_USERS.add(user_id)
    save_blocked()
    bot.reply_to(message, f"🚫 User {user_id} has been blocked.")

@bot.message_handler(commands=['unblock'])
def unblock_handler(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Only admins can unblock users.")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Usage:\n`/unblock [user_id]`", parse_mode="Markdown")
        return
    try:
        user_id = int(args[1])
    except:
        bot.reply_to(message, "❌ User ID must be an integer.")
        return
    if user_id not in BLOCKED_USERS:
        bot.reply_to(message, "ℹ️ This user is not blocked.")
        return
    BLOCKED_USERS.remove(user_id)
    save_blocked()
    bot.reply_to(message, f"✅ User {user_id} has been unblocked.")

# ========== Recording ==========
@bot.message_handler(commands=['rec'])
def rec_handler(message: Message):
    if is_blocked(message.from_user.id):
        bot.reply_to(message, "🚫 You are blocked from using this bot.")
        return
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Only admins can use this bot.")
        return

    args = message.text.split()
    if len(args) < 4:
        bot.reply_to(message, "❌ Usage:\n`/rec [m3u8_link] [duration] [filename]`", parse_mode="Markdown")
        return

    url, duration_str, filename = args[1], args[2], sanitize_filename(args[3])
    try:
        duration = int(duration_str)
        if duration <= 0:
            raise ValueError()
    except:
        bot.reply_to(message, "❌ Duration must be a positive integer (in seconds).")
        return

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    output_path = os.path.join(
        DOWNLOAD_DIR,
        f"{filename}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    )

    best_video_index = get_best_video_index(url)

    cmd = [
        "ffmpeg", "-y", "-i", url,
        "-map", f"0:{best_video_index}",
        "-map", "0:a?",
        "-t", str(duration),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-metadata", f"title={filename}",
        "-metadata", f"comment=Recorded by {WATERMARK}",
        output_path
    ]

    status_msg = bot.reply_to(message, "⏳ Recording started with best quality video...\nPlease wait...")

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for i in range(duration):
            time.sleep(1)
        process.wait()
        bot.edit_message_text("✅ Recording finished!", chat_id=message.chat.id, message_id=status_msg.message_id)
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Recording failed: {e}")
        return

    if os.path.exists(output_path):
        # If file is large, send as document
        filesize = os.path.getsize(output_path)
        try:
            if filesize > 50 * 1024 * 1024:  # 50MB
                with open(output_path, "rb") as video:
                    bot.send_document(message.chat.id, video, caption=f"🎬 Recording Complete: {filename}.mp4")
            else:
                with open(output_path, "rb") as video:
                    caption = f"""
🎬 *Recording Complete!*
📁 *Filename:* `{filename}.mp4`
🕓 *Duration:* `{duration}s`
💧 *Watermark:* {WATERMARK}
✅ Powered by *M3U8 Recorder Bot*
"""
                    bot.send_video(message.chat.id, video, caption=caption.strip(), parse_mode="Markdown")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Sending video failed: {e}")
    else:
        bot.send_message(message.chat.id, "❌ Recording failed.")

# ===================== START BOT =====================
print("✅ Bot is running...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
