import os
import subprocess
import datetime
import telebot
from telebot.types import Message
import json
import time
import logging

# ================= CONFIG =================
BOT_TOKEN = "7641596987:AAHYUJ0CTkK0jVCeYWpDwCgUYEdMqPeL0pY"
DOWNLOAD_DIR = "./downloads"
WATERMARK = "@JOYROCK10"
AUTO_SPLIT_SIZE = 1.95 * 1024 * 1024 * 1024  # 1.95 GB
DEFAULT_PART_DURATION = 3600  # seconds (1 hour per split)

bot = telebot.TeleBot(BOT_TOKEN)

# ===================== ADMIN / BLOCK SYSTEM =====================
ADMINS_FILE = 'admins.json'
BLOCKED_USERS_FILE = 'blocked.json'

# Load admins
if os.path.exists(ADMINS_FILE):
    with open(ADMINS_FILE, 'r') as f:
        ADMINS = json.load(f)
else:
    ADMINS = [123456789]  # Replace with your Telegram user ID
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

def probe_streams(url):
    cmd = ['ffprobe', '-v', 'error', '-show_entries',
           'stream=index,codec_type,codec_name,width,height', '-of', 'json', url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        data = json.loads(result.stdout)
        return data.get('streams', [])
    except Exception as e:
        logging.error(f"ffprobe error: {e}")
        return []

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

# ===================== ADMIN MANAGEMENT =====================
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

# ===================== BLOCK MANAGEMENT =====================
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

# ===================== RECORDING =====================
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

    logging.info(f"User {message.from_user.id} started recording: URL={url}, Duration={duration}, Filename={filename}")
    streams = probe_streams(url)
    if not streams:
        bot.reply_to(message, "❌ Could not detect streams from URL.")
        return

    video_streams = [s for s in streams if s.get('codec_type') == 'video' and 'width' in s]
    if not video_streams:
        bot.reply_to(message, "❌ No video stream found.")
        return

    best_video = max(video_streams, key=lambda s: s['width'])
    video_idx = best_video['index']
    audio_streams = [s for s in streams if s.get('codec_type') == 'audio']
    audio_idxs = [s['index'] for s in audio_streams]

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(DOWNLOAD_DIR, f"{filename}_{timestamp}.mp4")

    cmd = [
        'ffmpeg', '-y',
        '-reconnect', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '2',
        '-rw_timeout', '15000000',
        '-i', url,
        '-map', f'0:{video_idx}'
    ]
    for aidx in audio_idxs:
        cmd.extend(['-map', f'0:{aidx}'])

    cmd.extend([
        '-metadata', f'title={filename}',
        '-metadata', f'comment=Recorded by {WATERMARK}',
        '-t', str(duration),
        '-c:v', 'libx264',
        '-c:a', 'aac',
        output_path
    ])

    status_msg = bot.reply_to(message, "⏳ Recording started...\nPlease wait...")

    def update_progress(seconds, total, msg):
        percent = int((seconds / total) * 100)
        bar = '█' * (percent // 10) + '░' * (10 - (percent // 10))
        remaining = total - seconds
        try:
            bot.edit_message_text(
                f"⏳ Recording in progress...\n📊 Progress: [{bar}] {percent}%\n⏱️ Remaining: {remaining}s",
                chat_id=msg.chat.id,
                message_id=msg.message_id
            )
        except telebot.apihelper.ApiTelegramException:
            pass

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for i in range(duration):
            time.sleep(1)
            update_progress(i + 1, duration, status_msg)
        process.wait()

        bot.edit_message_text(
            f"✅ Recording finished!\n📊 Progress: [██████████] 100%",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )

    except Exception as e:
        bot.reply_to(message, f"❌ Recording failed: {e}")
        return

    if not os.path.exists(output_path):
        bot.reply_to(message, "❌ Recording failed, file not found.")
        return

    # =================== AUTO-SPLIT IF LARGE ===================
    file_size = os.path.getsize(output_path)
    if file_size >= AUTO_SPLIT_SIZE:
        bot.send_message(message.chat.id, f"⚡ File is larger than 1.95GB ({round(file_size/1024/1024/1024,2)}GB). Auto-splitting...")
        split_dir = os.path.join(DOWNLOAD_DIR, f"{filename}_parts")
        os.makedirs(split_dir, exist_ok=True)
        output_template = os.path.join(split_dir, f"{filename}_part%03d.mp4")
        split_cmd = [
            'ffmpeg', '-i', output_path,
            '-c', 'copy',
            '-map', '0',
            '-segment_time', str(DEFAULT_PART_DURATION),
            '-f', 'segment',
            output_template
        ]
        try:
            subprocess.run(split_cmd, check=True)
            parts = sorted(os.listdir(split_dir))
            bot.send_message(message.chat.id, f"✅ Auto-split complete! {len(parts)} parts created.")
            for part_file in parts:
                part_path = os.path.join(split_dir, part_file)
                if os.path.getsize(part_path) <= 50*1024*1024:  # Telegram upload limit
                    with open(part_path, 'rb') as p:
                        bot.send_video(message.chat.id, p, caption=f"📄 {part_file}")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Auto-split failed: {e}")
        return

    # =================== SEND VIDEO IF NOT LARGE ===================
    with open(output_path, "rb") as video:
        caption = f"""
🎬 *Recording Complete!*
📁 *Filename:* `{filename}.mp4`
🕓 *Duration:* `{duration}s`
💧 *Watermark:* {WATERMARK}
✅ Powered by *M3U8 Recorder Bot*
"""
        bot.send_video(message.chat.id, video, caption=caption.strip(), parse_mode="Markdown")

# ===================== START BOT =====================
print("✅ Bot is running...")
bot.infinity_polling()
