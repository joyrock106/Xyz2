import os
import subprocess
import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import json
import time
import threading
import logging

BOT_TOKEN = "8311688539:AAGZwrKz3xD51doqK8wdgBtZDWsa2YkEydw"
DOWNLOAD_DIR = "./downloads"
WATERMARK = "@JOYROCK10"

bot = telebot.TeleBot(BOT_TOKEN)

ADMINS_FILE = 'admins.json'

# Load admins from file
if os.path.exists(ADMINS_FILE):
    with open(ADMINS_FILE, 'r') as f:
        ADMINS = json.load(f)
else:
    ADMINS = [8078418903]
    with open(ADMINS_FILE, 'w') as f:
        json.dump(ADMINS, f)

BLOCKED_USERS_FILE = 'blocked.json'

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

def extract_screenshots(video_path, count=1):
    screenshots = []
    output_base = video_path.rsplit(".", 1)[0]
    duration_cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    try:
        result = subprocess.run(duration_cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        interval = duration / (count + 1)
    except:
        interval = 10

    for i in range(1, count + 1):
        timestamp = int(i * interval)
        img_path = f"{output_base}_ss{i}.jpg"
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(timestamp),
            "-vframes", "1",
            "-vf", "scale=640:-1",
            img_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if os.path.exists(img_path):
            screenshots.append(img_path)
    return screenshots

@bot.message_handler(commands=['start'])
def start_handler(message: Message):
    bot.send_message(message.chat.id, "🎬 M3U8 Recorder Bot এ স্বাগতম!\n\n"
                                      "রেকর্ড করতে:\n/rec [m3u8_link] [duration_seconds] [filename]\n\n"
                                      "শিডিউল করতে:\n/schedule YYYY-MM-DD HH:MM:SS URL DURATION FILENAME\n\n"
                                      "অ্যাডমিন যোগ করতে:\n/addadmin [user_id]\nঅ্যাডমিন মুছে ফেলতে:\n/removeadmin [user_id]\n"
                                      "লগ দেখতে:\n/log\n"
                                      "ব্যবহারকারীদের ব্লক করতে:\n/block [user_id]\n"
                                      "ব্লক উঠাতে:\n/unblock [user_id]")

@bot.message_handler(commands=['id'])
def id_handler(message: Message):
    bot.reply_to(message, f"🆔 আপনার ইউজার আইডি: `{message.from_user.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['addadmin'])
def add_admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ কেবল অ্যাডমিনরাই নতুন অ্যাডমিন যোগ করতে পারবেন।")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, "❌ ব্যবহার:\n`/addadmin [user_id]`", parse_mode="Markdown")
        return

    user_id = int(args[1])
    if user_id in ADMINS:
        bot.reply_to(message, "ℹ️ এই ইউজার ইতিমধ্যে অ্যাডমিন।")
    else:
        ADMINS.append(user_id)
        save_admins()
        bot.reply_to(message, f"✅ ইউজার `{user_id}` কে অ্যাডমিন হিসেবে যোগ করা হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['removeadmin'])
def remove_admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ কেবল অ্যাডমিনরাই অ্যাডমিন মুছে ফেলতে পারবেন।")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, "❌ ব্যবহার:\n`/removeadmin [user_id]`", parse_mode="Markdown")
        return

    user_id = int(args[1])
    if user_id not in ADMINS:
        bot.reply_to(message, "ℹ️ এই ইউজার অ্যাডমিন নয়।")
    else:
        ADMINS.remove(user_id)
        save_admins()
        bot.reply_to(message, f"✅ ইউজার `{user_id}` কে অ্যাডমিন তালিকা থেকে মুছে ফেলা হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['block'])
def block_user_cmd(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ কেবল অ্যাডমিনরাই ইউজার ব্লক করতে পারবেন।")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, "❌ ব্যবহার:\n`/block [user_id]`", parse_mode="Markdown")
        return

    user_id = int(args[1])
    if user_id in BLOCKED_USERS:
        bot.reply_to(message, "ℹ️ ইউজার ইতিমধ্যে ব্লক করা হয়েছে।")
    else:
        BLOCKED_USERS.add(user_id)
        save_blocked()
        bot.reply_to(message, f"🚫 ইউজার `{user_id}` কে ব্লক করা হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['unblock'])
def unblock_user_cmd(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ কেবল অ্যাডমিনরাই ইউজার আনব্লক করতে পারবেন।")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, "❌ ব্যবহার:\n`/unblock [user_id]`", parse_mode="Markdown")
        return

    user_id = int(args[1])
    if user_id not in BLOCKED_USERS:
        bot.reply_to(message, "ℹ️ ইউজার ব্লক করা হয়নি।")
    else:
        BLOCKED_USERS.remove(user_id)
        save_blocked()
        bot.reply_to(message, f"✅ ইউজার `{user_id}` আনব্লক করা হয়েছে।", parse_mode="Markdown")

@bot.message_handler(commands=['log'])
def log_handler(message: Message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ শুধুমাত্র অ্যাডমিনরা লগ দেখতে পারবেন।")
        return

    log_file = 'm3u8_recorder.log'
    if not os.path.exists(log_file):
        bot.reply_to(message, "⚠️ কোন লগ ফাইল পাওয়া যায়নি।")
        return

    with open(log_file, 'rb') as f:
        bot.send_document(message.chat.id, f, caption="📝 লগ ফাইল")

@bot.message_handler(commands=['rec'])
def rec_handler(message: Message):
    if is_blocked(message.from_user.id):
        bot.reply_to(message, "🚫 আপনি এই বট ব্যবহার করতে পারবেন না।")
        return
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ শুধুমাত্র অ্যাডমিন বট ব্যবহার করতে পারবেন।")
        return

    args = message.text.split()
    if len(args) < 4:
        bot.reply_to(message, "❌ ব্যবহার:\n`/rec [m3u8_link] [duration] [filename]`", parse_mode="Markdown")
        return

    url, duration_str, filename = args[1], args[2], sanitize_filename(args[3])
    try:
        duration = int(duration_str)
        if duration <= 0:
            raise ValueError()
    except:
        bot.reply_to(message, "❌ সময় (duration) সেকেন্ডে অবশ্যই একটি ধনাত্মক পূর্ণসংখ্যা হতে হবে।")
        return

    logging.info(f"User {message.from_user.id} started recording: URL={url}, Duration={duration}, Filename={filename}")

    streams = probe_streams(url)
    if not streams:
        bot.reply_to(message, "❌ URL থেকে স্ট্রিম সনাক্ত করা যায়নি।")
        logging.error(f"Recording failed: URL streams not found for user {message.from_user.id}")
        return

    video_streams = [s for s in streams if s.get('codec_type') == 'video' and 'width' in s]
    if not video_streams:
        bot.reply_to(message, "❌ ভিডিও স্ট্রিম পাওয়া যায়নি।")
        logging.error(f"Recording failed: No video streams found for user {message.from_user.id}")
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

    status_msg = bot.reply_to(message, "⏳ রেকর্ডিং শুরু হচ্ছে...\n⏱️ দয়া করে অপেক্ষা করুন...")

    def update_progress(seconds, total, msg):
        percent = int((seconds / total) * 100)
        bar = '█' * (percent // 10) + '░' * (10 - (percent // 10))
        remaining = total - seconds
        try:
            bot.edit_message_text(
                f"⏳ রেকর্ডিং চলছে...\n📊 অগ্রগতি: [{bar}] {percent}%\n⏱️ বাকি: {remaining}s",
                chat_id=msg.chat.id,
                message_id=msg.message_id
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                raise

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for i in range(duration):
            time.sleep(1)
            update_progress(i + 1, duration, status_msg)
        process.wait()

        bot.edit_message_text(
            f"✅ রেকর্ডিং সম্পন্ন!\n📊 অগ্রগতি: [██████████] 100%",
            chat_id=message.chat.id,
            message_id=status_msg.message_id
        )
        logging.info(f"Recording finished: File={output_path}")

    except Exception as e:
        bot.reply_to(message, f"❌ রেকর্ডিং ব্যর্থ হয়েছে: {e}")
        logging.error(f"Recording failed for user {message.from_user.id}: {e}")
        return

    if not os.path.exists(output_path):
        bot.reply_to(message, "❌ রেকর্ডিং ব্যর্থ হয়েছে, ফাইল পাওয়া যায়নি।")
        logging.error(f"Recording failed: Output file missing {output_path}")
        return

    screenshots = extract_screenshots(output_path, count=5)
    for img in screenshots:
        with open(img, "rb") as photo:
            bot.send_photo(message.chat.id, photo, caption="🖼 স্ক্রিনশট")
        os.remove(img)

    with open(output_path, "rb") as video:
        caption = f"""
🎬 *রেকর্ডিং সম্পন্ন!*
📁 *ফাইলের নাম:* `{filename}.mp4`
🕓 *দৈর্ঘ্য:* `{duration}s`
💧 *ওয়াটারমার্ক:* {WATERMARK}
✅ *M3U8 Recorder Bot* দ্বারা চালিত
"""
        bot.send_video(message.chat.id, video, caption=caption.strip(), parse_mode="Markdown")

# ------------------ Schedule feature ---------------------

def record_stream_scheduled(url, duration, chat_id, filename):
    logging.info(f"Scheduled recording started: ChatID={chat_id}, URL={url}, Duration={duration}, Filename={filename}")

    streams = probe_streams(url)
    if not streams:
        bot.send_message(chat_id, "❌ শিডিউলার: URL থেকে স্ট্রিম সনাক্ত করা যায়নি।")
        logging.error(f"Scheduled recording failed: No streams found. ChatID={chat_id}")
        return

    video_streams = [s for s in streams if s.get('codec_type') == 'video' and 'width' in s]
    if not video_streams:
        bot.send_message(chat_id, "❌ শিডিউলার: ভিডিও স্ট্রিম পাওয়া যায়নি।")
        logging.error(f"Scheduled recording failed: No video streams. ChatID={chat_id}")
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

    status_msg = bot.send_message(chat_id, f"⏳ শিডিউলার: রেকর্ডিং শুরু হচ্ছে... `{filename}`\n⏱️ অপেক্ষা করুন...")

    def update_progress(seconds, total, msg_id):
        percent = int((seconds / total) * 100)
        bar = '█' * (percent // 10) + '░' * (10 - (percent // 10))
        remaining = total - seconds
        try:
            bot.edit_message_text(
                f"⏳ শিডিউলার: রেকর্ডিং চলছে...\n📊 অগ্রগতি: [{bar}] {percent}%\n⏱️ বাকি: {remaining}s",
                chat_id=chat_id,
                message_id=msg_id
            )
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                raise

    try:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for i in range(duration):
            time.sleep(1)
            update_progress(i + 1, duration, status_msg.message_id)
        process.wait()

        bot.edit_message_text(
            f"✅ শিডিউলার: রেকর্ডিং সম্পন্ন!\n📊 অগ্রগতি: [██████████] 100%",
            chat_id=chat_id,
            message_id=status_msg.message_id
        )
        logging.info(f"Scheduled recording finished: File={output_path}")

    except Exception as e:
        bot.send_message(chat_id, f"❌ শিডিউলার: রেকর্ডিং ব্যর্থ হয়েছে: {e}")
        logging.error(f"Scheduled recording failed: ChatID={chat_id}, Error={e}")
        return

    if not os.path.exists(output_path):
        bot.send_message(chat_id, "❌ শিডিউলার: রেকর্ডিং ব্যর্থ হয়েছে, ফাইল পাওয়া যায়নি।")
        logging.error(f"Scheduled recording failed: Output file missing {output_path}")
        return

    screenshots = extract_screenshots(output_path, count=5)
    for img in screenshots:
        with open(img, "rb") as photo:
            bot.send_photo(chat_id, photo, caption="🖼 শিডিউলার স্ক্রিনশট")
        os.remove(img)

    with open(output_path, "rb") as video:
        caption = f"""
🎬 *শিডিউলার রেকর্ডিং সম্পন্ন!*
📁 *ফাইলের নাম:* `{filename}.mp4`
🕓 *দৈর্ঘ্য:* `{duration}s`
💧 *ওয়াটারমার্ক:* {WATERMARK}
✅ *M3U8 Recorder Bot* দ্বারা চালিত
"""
        bot.send_video(chat_id, video, caption=caption.strip(), parse_mode="Markdown")

@bot.message_handler(commands=['schedule'])
def schedule_handler(message: Message):
    if is_blocked(message.from_user.id):
        bot.reply_to(message, "🚫 আপনি এই বট ব্যবহার করতে পারবেন না।")
        return
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ শুধুমাত্র অ্যাডমিন বট ব্যবহার করতে পারবেন।")
        return

    args = message.text.split(maxsplit=6)
    # Expected: /schedule YYYY-MM-DD HH:MM:SS URL DURATION FILENAME
    if len(args) < 7:
        bot.reply_to(message, "❌ ব্যবহার:\n`/schedule YYYY-MM-DD HH:MM:SS URL DURATION FILENAME`", parse_mode="Markdown")
        return

    date_str, time_str, url, duration_str, filename = args[1], args[2], args[3], args[4], sanitize_filename(args[5])
    datetime_str = f"{date_str} {time_str}"

    try:
        scheduled_time = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        if scheduled_time <= datetime.datetime.now():
            bot.reply_to(message, "❌ শিডিউল সময় অবশ্যই ভবিষ্যতের হওয়া উচিত।")
            return
    except Exception:
        bot.reply_to(message, "❌ তারিখ এবং সময় সঠিক ফরম্যাটে দিন: `YYYY-MM-DD HH:MM:SS`", parse_mode="Markdown")
        return

    try:
        duration = int(duration_str)
        if duration <= 0:
            raise ValueError()
    except:
        bot.reply_to(message, "❌ সময় (duration) সেকেন্ডে অবশ্যই একটি ধনাত্মক পূর্ণসংখ্যা হতে হবে।")
        return

    delay = (scheduled_time - datetime.datetime.now()).total_seconds()
    bot.reply_to(message, f"✅ রেকর্ডিং `{filename}` শিডিউল করা হয়েছে {scheduled_time} এ।")

    def job():
        record_stream_scheduled(url, duration, message.chat.id, filename)

    threading.Timer(delay, job).start()

print("✅ Bot is running...")
bot.infinity_polling()
