import telebot

# Replace with your bot token
BOT_TOKEN = "8311688539:AAGZwrKz3xD51doqK8wdgBtZDWsa2YkEydw"

bot = telebot.TeleBot(BOT_TOKEN)

# /start command
@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, "Hello! 👋 I'm your simple Telegram bot.")

# Any text message
@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.reply_to(message, f"You said: {message.text}")

print("Bot is running...")
bot.polling()
