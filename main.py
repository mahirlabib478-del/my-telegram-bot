import os
import time
import threading
from flask import Flask
import telebot
from telebot import types

# =========================
# CONFIG
# =========================
TOKEN = "8235614816:AAHxzXryEh4h9h20njdFMZCRx8Z_YQGkdOM"
ADMIN_ID = 8538304896

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

users = {}
# Set to store unique user IDs for broadcast
broadcast_users = set()

# =========================
# WEB SERVER
# =========================
@app.route('/')
def home():
    return "Bot is running!"

# =========================
# START COMMAND
# =========================
@bot.message_handler(commands=['start'])
def start(message):
    # Add user to broadcast list
    broadcast_users.add(message.chat.id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Sell")

    bot.send_message(
        message.chat.id,
        "👋 Welcome to our bot!\n\n"
        "এখানে আপনি Instagram 2FA account Sell দিতে পারবেন।",
        reply_markup=markup
    )

# =========================
# BROADCAST COMMAND (ADMIN ONLY)
# =========================
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.chat.id == ADMIN_ID:
        # Extract the message content after /broadcast
        msg_text = message.text.replace("/broadcast", "").strip()
        
        if not msg_text:
            bot.reply_to(message, "⚠️ দয়া করে বার্তার টেক্সট দিন। যেমন: /broadcast হ্যালো সবাই")
            return

        count = 0
        for chat_id in broadcast_users:
            try:
                bot.send_message(chat_id, msg_text)
                count += 1
            except Exception as e:
                print(f"Failed to send to {chat_id}: {e}")
        
        bot.reply_to(message, f"✅ {count} জন ব্যবহারকারীকে বার্তা পাঠানো হয়েছে।")
    else:
        bot.reply_to(message, "🚫 এই কমান্ডটি শুধুমাত্র অ্যাডমিনের জন্য।")

# =========================
# SELL BUTTON
# =========================
@bot.message_handler(func=lambda m: m.text == "Sell")
def sell(message):

    users[message.chat.id] = {"step": "part1"}

    bot.send_message(
        message.chat.id,
        "📌 সিরিয়াল অনুযায়ী username লিস্ট দিন"
    )

# =========================
# MAIN TEXT HANDLER
# =========================
@bot.message_handler(content_types=['text'])
def handle(message):

    chat_id = message.chat.id

    if chat_id not in users:
        return

    step = users[chat_id]["step"]

    # PART 1
    if step == "part1":

        users[chat_id]["part1"] = message.text
        users[chat_id]["step"] = "part2"

        bot.send_message(
            chat_id,
            "📌 সিরিয়াল অনুযায়ী password লিস্ট দিন"
        )

    # PART 2
    elif step == "part2":

        users[chat_id]["part2"] = message.text
        users[chat_id]["step"] = "part3"

        bot.send_message(
            chat_id,
            "📌 সিরিয়াল অনুযায়ী 2FA লিস্ট দিন"
        )

    # PART 3
    elif step == "part3":

        users[chat_id]["part3"] = message.text
        users[chat_id]["step"] = "bkash"

        bot.send_message(
            chat_id,
            "📌 bKash নাম্বার দিন"
        )

    # BKASH STEP
    elif step == "bkash":

        users[chat_id]["bkash"] = message.text

        data = users[chat_id]

        username = message.from_user.username
        username_text = f"@{username}" if username else "No Username"

        admin_msg = (
            f"🔥 New Sell Request\n\n"
            f"User ID: {message.from_user.id}\n"
            f"Username: {username_text}\n\n"
            f"1M:\n{data['part1']}\n\n"
            f"2M:\n{data['part2']}\n\n"
            f"2FA:\n{data['part3']}\n\n"
            f"bKash: {data['bkash']}"
        )

        try:
            bot.send_message(ADMIN_ID, admin_msg)

            bot.send_message(
                chat_id,
                "✅ আপনার তথ্য নেওয়া হয়েছে\n\n"
                "আপনার bKash এ পেমেন্ট প্রক্রিয়াধীন।"
            )

        except Exception as e:
            print("Error:", e)

        del users[chat_id]

# =========================
# BOT POLLING THREAD
# =========================
def run_bot():

    print("🤖 Bot Running...")

    while True:
        try:
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=60
            )

        except Exception as e:
            print(f"Polling Error: {e}")
            time.sleep(5)

# =========================
# MAIN
# =========================
if __name__ == "__main__":

    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))

    app.run(host="0.0.0.0", port=port)
