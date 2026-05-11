import telebot
from telebot import types

TOKEN = "7995124159:AAGUOXpN5rPiboAsbAVwFOmLG572v7AIWJc"
ADMIN_ID = 8538304896

bot = telebot.TeleBot(TOKEN)

users = {}

# START COMMAND
@bot.message_handler(commands=['start'])
def start(message):

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Sell")

    bot.send_message(
        message.chat.id,
        "👋 Welcome to our bot!\n\n"
        "এখানে আপনি ইনস্টাগ্রাম ২ fa আইডি Sell দিতে পারবেন।",
        reply_markup=markup
    )

# SELL BUTTON
@bot.message_handler(func=lambda m: m.text == "Sell")
def sell(message):

    users[message.chat.id] = {"step": "part1"}

    bot.send_message(
        message.chat.id,
        "📌 সিরিয়াল অনুযায়ী ইউজারনেম লিস্ট দিন"
    )

# MAIN TEXT HANDLER
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

        bot.send_message(chat_id, "📌 সিরিয়াল অনুযায়ী পাসওয়ার্ড লিস্ট দিন")

    # PART 2
    elif step == "part2":
        users[chat_id]["part2"] = message.text
        users[chat_id]["step"] = "part3"

        bot.send_message(chat_id, "📌 সিরিয়াল অনুযায়ী 2FA লিস্ট দিন")

    # PART 3
    elif step == "part3":
        users[chat_id]["part3"] = message.text
        users[chat_id]["step"] = "bkash"

        bot.send_message(chat_id, "📌 bKash নাম্বার দিন")

    # BKASH STEP
    elif step == "bkash":

        users[chat_id]["bkash"] = message.text
        data = users[chat_id]

        # username handling
        username = message.from_user.username
        username_text = f"@{username}" if username else "No Username"

        # ADMIN MESSAGE
        admin_msg = (
            f"🔥 New Sell Request\n\n"
            f"User ID: {message.from_user.id}\n"
            f"Username: {username_text}\n\n"
            f"Part 1: {data['part1']}\n"
            f"Part 2: {data['part2']}\n"
            f"Part 3: {data['part3']}\n\n"
            f"bKash: {data['bkash']}"
        )

        bot.send_message(ADMIN_ID, admin_msg)

        # USER CONFIRMATION
        bot.send_message(
            chat_id,
            "✅ আপনার তথ্য নেওয়া হয়েছে\n\n"
            "আপনার bKash এ পেমেন্ট প্রক্রিয়াধীন।"
        )

        del users[chat_id]

print("Bot Running...")
bot.infinity_polling()
