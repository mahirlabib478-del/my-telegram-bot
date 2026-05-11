import os
import time
import threading
from flask import Flask
import telebot
from telebot import types
from pymongo import MongoClient

# =========================
# CONFIG & MONGODB
# =========================
TOKEN = "8235614816:AAHxzXryEh4h9h20njdFMZCRx8Z_YQGkdOM"
ADMIN_ID = 8538304896
# আপনার MongoDB URI এখানে দিন
MONGO_URI = "mongodb+srv://mahirlabib478:labib2000@cluster0.ebpwzvi.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)
db = client["telegram_bot_db"]

# MongoDB Collections (Dict এর বিকল্প)
users_db = db["users"]          # user_data
wallets_db = db["wallets"]      # wallets
pending_db = db["pending"]      # pending_approvals
support_db = db["support"]      # support_mode
session_db = db["sessions"]     # users (steps/flow)

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

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
    username = message.from_user.username
    users_db.update_one({"chat_id": message.chat.id}, {"$set": {"username": username if username else "No username"}}, upsert=True)
    
    if not wallets_db.find_one({"chat_id": message.chat.id}):
        wallets_db.insert_one({"chat_id": message.chat.id, "balance": 0.0})

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Sell", "Wallet", "Support")

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
    support_db.update_one({"chat_id": message.chat.id}, {"$set": {"mode": True}}, upsert=True)
    bot.send_message(message.chat.id, "📩 আপনার মেসেজটি নিচে লিখুন, অ্যাডমিন আপনাকে শীঘ্রই উত্তর দেবেন।")

# =========================
# ADMIN COMMANDS
# =========================
@bot.message_handler(commands=['broadcast', 'send', 'users'])
def admin_commands(message):
    if message.chat.id != ADMIN_ID: return

    if message.text.startswith('/broadcast'):
        msg_text = message.text.replace("/broadcast", "").strip()
        if not msg_text: return
        all_users = users_db.find()
        for u in all_users:
            try: bot.send_message(u["chat_id"], msg_text)
            except: continue
        bot.reply_to(message, "✅ সবাইকে পাঠানো হয়েছে।")

    elif message.text.startswith('/send'):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3: return
        try:
            bot.send_message(parts[1], f"👤 অ্যাডমিন থেকে মেসেজ:\n{parts[2]}")
            bot.reply_to(message, "✅ পাঠানো হয়েছে।")
        except Exception as e:
            bot.reply_to(message, f"❌ ব্যর্থ: {e}")

    elif message.text.startswith('/users'):
        all_users = list(users_db.find())
        if not all_users:
            bot.reply_to(message, "⚠️ কোন ইউজার পাওয়া যায়নি।")
        else:
            list_text = f"📊 মোট ইউজার: {len(all_users)}\n\nID | Username\n"
            for u in all_users:
                list_text += f"{u['chat_id']} | @{u.get('username', 'N/A')}\n"
            bot.reply_to(message, list_text if len(list_text) < 4000 else list_text[:4000])

# =========================
# SELL BUTTON
# =========================
@bot.message_handler(func=lambda m: m.text == "Sell")
def sell_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Regular 2FA ID (3.10 BDT)", callback_data="sell_regular"))
    markup.add(types.InlineKeyboardButton("✅ 1 Day Old 2FA ID (2.00 BDT)", callback_data="sell_1day"))
    bot.send_message(message.chat.id, "📌 অনুগ্রহ করে একটি ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("sell_"))
def process_sell_choice(call):
    chat_id = call.message.chat.id
    category = "Regular 2FA ID" if call.data == "sell_regular" else "1 Day Old 2FA ID"
    session_db.update_one({"chat_id": chat_id}, {"$set": {"step": "part1", "category": category}}, upsert=True)
    bot.edit_message_text(f"📌 আপনি সিলেক্ট করেছেন: {category}\n\nএখন সিরিয়াল অনুযায়ী username লিস্ট দিন:", chat_id, call.message.message_id)

# =========================
# WALLET
# =========================
@bot.message_handler(func=lambda m: m.text == "Wallet")
def show_wallet(message):
    user_wallet = wallets_db.find_one({"chat_id": message.chat.id})
    balance = user_wallet["balance"] if user_wallet else 0.0
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💸 bKash Withdraw", callback_data="withdraw_bkash"))
    bot.send_message(message.chat.id, f"💰 আপনার বর্তমান ব্যালেন্স: {balance} BDT", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "withdraw_bkash")
def withdraw_request(call):
    session_db.update_one({"chat_id": call.message.chat.id}, {"$set": {"step": "w_amount"}}, upsert=True)
    bot.edit_message_text("📌 কত টাকা উইথড্র করতে চান? (শুধুমাত্র সংখ্যা দিন):", call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['text'])
def handle(message):
    chat_id = message.chat.id
    
    # Support Mode
    sup = support_db.find_one({"chat_id": chat_id})
    if sup and sup.get("mode"):
        username = message.from_user.username or "No username"
        bot.send_message(ADMIN_ID, f"📩 Support: {message.text}\nFrom ID: {chat_id}\nUsername: @{username}")
        bot.send_message(chat_id, "✅ মেসেজটি পাঠানো হয়েছে।")
        support_db.update_one({"chat_id": chat_id}, {"$set": {"mode": False}})
        return

    # Admin Deposit
    pending = pending_db.find_one({"admin_chat_id": ADMIN_ID})
    if chat_id == ADMIN_ID and pending:
        try:
            amount = float(message.text)
            target = pending["target_id"]
            wallets_db.update_one({"chat_id": target}, {"$inc": {"balance": amount}}, upsert=True)
            bot.send_message(target, f"✅ পেমেন্ট নিশ্চিত! {amount} টাকা যোগ হয়েছে।")
            pending_db.delete_one({"admin_chat_id": ADMIN_ID})
            return
        except: bot.send_message(chat_id, "⚠️ ভুল সংখ্যা!")

    # User Input Logic
    data = session_db.find_one({"chat_id": chat_id})
    if data:
        step = data.get("step")
        if step == "w_amount":
            try:
                amt = float(message.text)
                user_wallet = wallets_db.find_one({"chat_id": chat_id})
                if amt > (user_wallet["balance"] if user_wallet else 0):
                    bot.send_message(chat_id, "⚠️ আপনার পর্যাপ্ত ব্যালেন্স নেই।")
                    session_db.delete_one({"chat_id": chat_id})
                    return
                session_db.update_one({"chat_id": chat_id}, {"$set": {"w_amount": amt, "step": "w_number"}})
                bot.send_message(chat_id, "📌 আপনার bKash নাম্বারটি দিন:")
            except: bot.send_message(chat_id, "⚠️ ভুল সংখ্যা!")
        
        elif step == "w_number":
            amt = data["w_amount"]
            number = message.text
            user = message.from_user.username or "N/A"
            admin_text = f"🚨 New bKash Withdrawal\nUser: @{user}\nAmount: {amt} BDT\nbKash Number: {number}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Paid", callback_data=f"wpay_{chat_id}_{amt}"), types.InlineKeyboardButton("❌ Deny", callback_data=f"wdeny_{chat_id}"))
            bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
            bot.send_message(chat_id, "✅ আপনার উইথড্র রিকোয়েস্টটি অ্যাডমিনের কাছে পাঠানো হয়েছে।")
            session_db.delete_one({"chat_id": chat_id})

        elif step in["part1", "part2", "part3", "bkash"]:
            if step == "part1":
                session_db.update_one({"chat_id": chat_id}, {"$set": {"part1": message.text, "step": "part2"}})
                bot.send_message(chat_id, "📌 password লিস্ট দিন")
            elif step == "part2":
                session_db.update_one({"chat_id": chat_id}, {"$set": {"part2": message.text, "step": "part3"}})
                bot.send_message(chat_id, "📌 2FA লিস্ট দিন")
            elif step == "part3":
                session_db.update_one({"chat_id": chat_id}, {"$set": {"part3": message.text, "step": "bkash"}})
                bot.send_message(chat_id, "📌 bKash নাম্বার দিন")
            elif step == "bkash":
                final_data = session_db.find_one({"chat_id": chat_id})
                username = message.from_user.username or "No username"
                admin_msg = f"🔥 New Sell: {final_data['category']}\nUser ID: {chat_id}\nUsername: @{username}\n\n1M: {final_data['part1']}\n2M: {final_data['part2']}\n2FA: {final_data['part3']}\nBKash: {message.text}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{chat_id}"), types.InlineKeyboardButton("❌ Deny", callback_data=f"deny_{chat_id}"))
                bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
                bot.send_message(chat_id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")
                session_db.delete_one({"chat_id": chat_id})

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("approve_"):
        uid = int(call.data.split("_")[1])
        pending_db.update_one({"admin_chat_id": ADMIN_ID}, {"$set": {"target_id": uid}}, upsert=True)
        bot.edit_message_text("✅ অনুমোদিত। ব্যালেন্স লিখুন:", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("deny_"):
        bot.send_message(int(call.data.split("_")[1]), "❌ দুঃখিত, আপনার রিকোয়েস্টটি রিজেক্ট করা হয়েছে।")
        bot.edit_message_text("❌ রিজেক্ট করা হয়েছে।", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("wpay_"):
        _, uid, amt = call.data.split("_")
        wallets_db.update_one({"chat_id": int(uid)}, {"$inc": {"balance": -float(amt)}})
        bot.send_message(uid, f"✅ আপনার {amt} BDT উইথড্র সম্পন্ন হয়েছে!")
        bot.edit_message_text("✅ পেমেন্ট করা হয়েছে।", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("wdeny_"):
        bot.send_message(int(call.data.split("_")[1]), "❌ আপনার উইথড্র রিকোয়েস্টটি রিজেক্ট করা হয়েছে।")
        bot.edit_message_text("❌ রিজেক্ট করা হয়েছে।", call.message.chat.id, call.message.message_id)

def run_bot():
    while True:
        try: bot.infinity_polling()
        except: time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
