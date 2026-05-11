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
broadcast_users = set()
wallets = {} 
pending_approvals = {} 
support_mode = {} # {chat_id: True/False}

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
    broadcast_users.add(message.chat.id)
    if message.chat.id not in wallets:
        wallets[message.chat.id] = 0.0

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Sell", "Wallet", "Support") # Support বাটন যোগ করা হয়েছে

    bot.send_message(
        message.chat.id,
        "👋 Welcome to our bot!\n\n"
        "এখানে আপনি Instagram 2FA account Sell দিতে পারবেন।",
        reply_markup=markup
    )

# =========================
# SUPPORT SYSTEM
# =========================
@bot.message_handler(func=lambda m: m.text == "Support")
def support(message):
    support_mode[message.chat.id] = True
    bot.send_message(message.chat.id, "📩 আপনার মেসেজটি নিচে লিখুন, অ্যাডমিন আপনাকে শীঘ্রই উত্তর দেবেন।")

# =========================
# BROADCAST & SEND COMMANDS (ADMIN ONLY)
# =========================
@bot.message_handler(commands=['broadcast', 'send'])
def admin_commands(message):
    if message.chat.id != ADMIN_ID:
        return

    if message.text.startswith('/broadcast'):
        msg_text = message.text.replace("/broadcast", "").strip()
        if not msg_text: return
        for user_id in broadcast_users:
            try: bot.send_message(user_id, msg_text)
            except: continue
        bot.reply_to(message, "✅ সবাইকে পাঠানো হয়েছে।")

    elif message.text.startswith('/send'):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3: return
        target_id, msg_text = parts[1], parts[2]
        try:
            bot.send_message(target_id, f"👤 অ্যাডমিন থেকে মেসেজ:\n{msg_text}")
            bot.reply_to(message, "✅ পাঠানো হয়েছে।")
        except Exception as e:
            bot.reply_to(message, f"❌ ব্যর্থ: {e}")

# =========================
# WALLET & SELL
# =========================
@bot.message_handler(func=lambda m: m.text == "Wallet")
def show_wallet(message):
    balance = wallets.get(message.chat.id, 0.0)
    bot.send_message(message.chat.id, f"💰 আপনার বর্তমান ব্যালেন্স: {balance} BDT")

@bot.message_handler(func=lambda m: m.text == "Sell")
def sell(message):
    users[message.chat.id] = {"step": "part1"}
    bot.send_message(message.chat.id, "📌 সিরিয়াল অনুযায়ী username লিস্ট দিন")

# =========================
# MAIN TEXT HANDLER
# =========================
@bot.message_handler(content_types=['text'])
def handle(message):
    chat_id = message.chat.id

    # ১. ইউজার যদি অ্যাডমিনের কাছে সাপোর্ট মেসেজ পাঠায়
    if support_mode.get(chat_id):
        bot.send_message(ADMIN_ID, f"📩 New Support Message\nFrom: {chat_id}\n\nMessage: {message.text}\n\nরিপ্লাই দিতে টাইপ করুন: /send {chat_id} [আপনার রিপ্লাই]")
        bot.send_message(chat_id, "✅ আপনার মেসেজটি অ্যাডমিনের কাছে পৌঁছেছে।")
        support_mode[chat_id] = False
        return

    # ২. অ্যাডমিন যদি পেন্ডিং এপ্রুভাল এর ব্যালেন্স যোগ করতে চায়
    if chat_id == ADMIN_ID and chat_id in pending_approvals:
        try:
            amount = float(message.text)
            target_user_id = pending_approvals[chat_id]
            wallets[target_user_id] = wallets.get(target_user_id, 0) + amount
            bot.send_message(target_user_id, f"✅ পেমেন্ট নিশ্চিত! {amount} টাকা যোগ করা হয়েছে।")
            bot.send_message(chat_id, f"✅ সফলভাবে {amount} টাকা ইউজারকে দেওয়া হয়েছে।")
            del pending_approvals[chat_id]
            return
        except ValueError:
            bot.send_message(chat_id, "⚠️ দয়া করে একটি সঠিক সংখ্যা লিখুন।")
            return

    # ৩. নরমাল ইউজার স্টেপস
    if chat_id in users:
        step = users[chat_id]["step"]
        if step == "part1":
            users[chat_id]["part1"] = message.text
            users[chat_id]["step"] = "part2"
            bot.send_message(chat_id, "📌 সিরিয়াল অনুযায়ী password লিস্ট দিন")
        elif step == "part2":
            users[chat_id]["part2"] = message.text
            users[chat_id]["step"] = "part3"
            bot.send_message(chat_id, "📌 সিরিয়াল অনুযায়ী 2FA লিস্ট দিন")
        elif step == "part3":
            users[chat_id]["part3"] = message.text
            users[chat_id]["step"] = "bkash"
            bot.send_message(chat_id, "📌 bKash নাম্বার দিন")
        elif step == "bkash":
            users[chat_id]["bkash"] = message.text
            data = users[chat_id]
            admin_msg = (f"🔥 New Sell Request\nUser ID: {chat_id}\n\n1M: {data['part1']}\n2M: {data['part2']}\n2FA: {data['part3']}\nBKash: {data['bkash']}")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{chat_id}"),
                       types.InlineKeyboardButton("❌ Deny", callback_data=f"deny_{chat_id}"))
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
            bot.send_message(chat_id, "✅ আপনার তথ্য অ্যাডমিনের কাছে পাঠানো হয়েছে।")
            del users[chat_id]

# (CALLBACK HANDLER ও RUN_BOT এর কোড আগের মতোই আছে)
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("approve_"):
        user_id = int(call.data.split("_")[1])
        pending_approvals[call.message.chat.id] = user_id
        bot.edit_message_text("✅ অনুমোদিত। ব্যালেন্স লিখুন:", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("deny_"):
        user_id = int(call.data.split("_")[1])
        bot.edit_message_text("❌ বাতিল করা হয়েছে।", call.message.chat.id, call.message.message_id)
        bot.send_message(user_id, "❌ আপনার সেল রিকোয়েস্টটি রিজেক্ট করা হয়েছে।")

def run_bot():
    while True:
        try: bot.infinity_polling()
        except: time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
