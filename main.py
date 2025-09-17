from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters
from pytube import YouTube
import os

# Dictionary to temporarily store user URLs
user_urls = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send me a YouTube link and I'll download the video for you.")

# Receive YouTube link
async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    user_id = update.message.from_user.id
    try:
        yt = YouTube(url)
        user_urls[user_id] = yt  # Store the YouTube object

        # Create quality buttons
        buttons = []
        for stream in yt.streams.filter(progressive=True).order_by('resolution').desc():
            buttons.append([InlineKeyboardButton(stream.resolution, callback_data=stream.itag)])

        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text("Choose the quality:", reply_markup=reply_markup)

    except Exception as e:
        await update.message.reply_text(f"Failed to fetch video info. Error: {e}")

# Handle quality selection
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in user_urls:
        await query.edit_message_text("Please send a YouTube link first.")
        return

    yt = user_urls[user_id]
    itag = int(query.data)

    try:
        stream = yt.streams.get_by_itag(itag)
        file_path = stream.download()
        await query.edit_message_text(f"Downloading: {yt.title}")

        # Send video
        await context.bot.send_video(chat_id=query.message.chat.id, video=open(file_path, 'rb'), caption=f"Downloaded: {yt.title}")

        os.remove(file_path)
        del user_urls[user_id]  # Clean up

    except Exception as e:
        await query.edit_message_text(f"Failed to download video. Error: {e}")

if __name__ == "__main__":
    TOKEN = "8058984373:AAGG-PuynpRquzavA3K1IXihAA13QEl5gwE"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_link))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()
