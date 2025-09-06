import os
import subprocess
import datetime
import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import json
import time
import uuid

# ===================== CONFIG =====================
BOT_TOKEN = "7986001230:AAHHfZKYnip33tt9uccDNvTe47bdMNgJSbM"  # 🔴 Replace with your Bot Token
DOWNLOAD_DIR = "./downloads"
WATERMARK = "@SURAJVAI"

bot = telebot.TeleBot(BOT_TOKEN)

# ===================== ADMIN / BLOCK SYSTEM =====================
ADMINS_FILE = 'admins.json'
BLOCKED_USERS_FILE = 'blocked.json'

# Load admins
if os.path.exists(ADMINS_FILE):
    with open(ADMINS_FILE, 'r') as f:
        ADMINS = json.load(f)
else:
    ADMINS = [8078418903]  # 🔴 Put your Telegram ID here
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
    """Sanitize the filename to avoid illegal characters."""
    return "".join(c for c in name if c.isalnum() or c in ('_', '-'))[:50]

# ===================== TASK STORAGE =====================
# Store recording tasks temporarily
RECORDING_TASKS = {}  # key -> (url, duration, filename)

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

# ========== Recording with Inline Options ==========
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

    # Store recording task with short UUID key
    task_id = str(uuid.uuid4())[:8]
    RECORDING_TASKS[task_id] = (url, duration, filename)

    # Inline buttons
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Multi Audio+Video", callback_data=f"multi|{task_id}"))
    markup.add(InlineKeyboardButton("🎯 Default Single Stream", callback_data=f"single|{task_id}"))

    bot.send_message(message.chat.id, "Select recording type:", reply_markup=markup)

# Handle inline button callback
@bot.callback_query_handler(func=lambda call: True)
def callback_rec(call: CallbackQuery):
    try:
        choice, task_id = call.data.split("|")
        if task_id not in RECORDING_TASKS:
            bot.send_message(call.message.chat.id, "❌ Task expired or invalid!")
            return

        url, duration, filename = RECORDING_TASKS.pop(task_id)

        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)

        output_path = os.path.join(DOWNLOAD_DIR, f"{filename}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")

        # FFmpeg command
        if choice == "multi":
            cmd = [
                "ffmpeg", "-y", "-i", url,
                "-map", "0",  # all streams (video+audio)
                "-t", str(duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-metadata", f"title={filename}",
                "-metadata", f"comment=Recorded by {WATERMARK}",
                output_path
            ]
        else:  # single stream
            cmd = [
                "ffmpeg", "-y", "-i", url,
                "-map", "0:v:0",  # first video stream
                "-map", "0:a",    # all audio streams
                "-t", str(duration),
                "-c:v", "libx264",
                "-c:a", "aac",
                "-metadata", f"title={filename}",
                "-metadata", f"comment=Recorded by {WATERMARK}",
                output_path
            ]

        status_msg = bot.send_message(call.message.chat.id, "⏳ Recording started...\nPlease wait...")

        # Run FFmpeg
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for i in range(duration):
            time.sleep(1)
        process.wait()
        bot.edit_message_text("✅ Recording finished!", chat_id=call.message.chat.id, message_id=status_msg.message_id)

        # Send video
        if os.path.exists(output_path):
            with open(output_path, "rb") as video:
                caption = f"""
🎬 *Recording Complete!*
📁 *Filename:* `{filename}.mp4`
🕓 *Duration:* `{duration}s`
💧 *Watermark:* {WATERMARK}
✅ Powered by *M3U8 Recorder Bot*
"""
                bot.send_video(call.message.chat.id, video, caption=caption.strip(), parse_mode="Markdown")
        else:
            bot.send_message(call.message.chat.id, "❌ Recording failed.")

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Error: {e}")

# ===================== START BOT =====================
print("✅ Bot is running...")
bot.infinity_polling()
