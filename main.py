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

# বাটন নাম স্টোর করার জন্য ডিকশনারি
button_labels = {
    "btn1": "Sell",
    "btn2": "Wallet",
    "btn3": "Support",
    "sell1": "Regular 2FA ID (3.10 BDT)",
    "sell2": "1 Day Old 2FA ID (2.00 BDT)"
}

users = {}
user_data = {}  # Stores {chat_id: username}
wallets = {} 
pending_approvals = {} 
support_mode = {} 

# =========================
# HELPER: Generate Main Markup
# =========================
def get_main_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(button_labels["btn1"], button_labels["btn2"], button_labels["btn3"])
    return markup

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
    user_data[message.chat.id] = username if username else "No username"
    
    if message.chat.id not in wallets:
        wallets[message.chat.id] = 0.0

    bot.send_message(
        message.chat.id,
        "👋 Welcome to our bot!\n\n"
        "এখানে আপনি Instagram 2FA account Sell দিতে পারবেন।",
        reply_markup=get_main_markup()
    )

# =========================
# ADMIN COMMANDS
# =========================
@bot.message_handler(commands=['broadcast', 'send', 'users', 'setbal', 'checkbal', 'setbtn'])
def admin_commands(message):
    if message.chat.id != ADMIN_ID: return

    # বাটন নাম পরিবর্তন
    if message.text.startswith('/setbtn'):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3 or parts[1] not in button_labels:
            bot.reply_to(message, "⚠️ ব্যবহার: /setbtn [key] [নাম]\nKeys: btn1, btn2, btn3, sell1, sell2")
            return
        button_labels[parts[1]] = parts[2]
        bot.reply_to(message, f"✅ {parts[1]} এর নাম পরিবর্তন করে '{parts[2]}' রাখা হয়েছে।")
        return

    # ব্রডকাস্ট কমান্ড
    if message.text.startswith('/broadcast'):
        msg_text = message.text.replace("/broadcast", "").strip()
        if not msg_text: return
        for user_id in user_data:
            try: bot.send_message(user_id, msg_text)
            except: continue
        bot.reply_to(message, "✅ সবাইকে পাঠানো হয়েছে।")

    # মেসেজ পাঠানো
    elif message.text.startswith('/send'):
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3: return
        try:
            bot.send_message(parts[1], f"👤 অ্যাডমিন থেকে মেসেজ:\n{parts[2]}")
            bot.reply_to(message, "✅ পাঠানো হয়েছে।")
        except Exception as e:
            bot.reply_to(message, f"❌ ব্যর্থ: {e}")

    # ইউজার এবং ব্যালেন্স
    elif message.text.startswith('/users'):
        if not user_data:
            bot.reply_to(message, "⚠️ কোন ইউজার পাওয়া যায়নি।")
        else:
            list_text = f"📊 মোট ইউজার: {len(user_data)}\n\nID | Username | Balance\n--------------------------\n"
            for uid, uname in user_data.items():
                balance = wallets.get(uid, 0.0)
                list_text += f"{uid} | @{uname} | {balance} BDT\n"
            for x in range(0, len(list_text), 4000):
                bot.reply_to(message, list_text[x:x+4000])

    # ব্যালেন্স সেট
    elif message.text.startswith('/setbal'):
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "⚠️ ব্যবহার: /setbal[user_id] [amount]")
            return
        try:
            target_id = int(parts[1])
            new_balance = float(parts[2])
            wallets[target_id] = new_balance
            bot.reply_to(message, f"✅ ইউজার {target_id}-এর নতুন ব্যালেন্স: {new_balance} BDT")
        except:
            bot.reply_to(message, "❌ ভুল ফরম্যাট।")

    # ব্যালেন্স চেক
    elif message.text.startswith('/checkbal'):
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ ব্যবহার: /checkbal [user_id]")
            return
        try:
            target_id = int(parts[1])
            balance = wallets.get(target_id, 0.0)
            username = user_data.get(target_id, "Unknown")
            bot.reply_to(message, f"🔍 ইউজার ইনফো:\n\n🆔 আইডি: {target_id}\n👤 ইউজারনেম: @{username}\n💰 ব্যালেন্স: {balance} BDT")
        except:
            bot.reply_to(message, "❌ ইউজার খুঁজে পাওয়া যায়নি।")

# =========================
# MAIN MESSAGE HANDLER
# =========================
@bot.message_handler(func=lambda m: True)
def handle(message):
    chat_id = message.chat.id
    
    # বাটন লজিক
    if message.text == button_labels["btn1"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(button_labels["sell1"], callback_data="sell_regular"))
        markup.add(types.InlineKeyboardButton(button_labels["sell2"], callback_data="sell_1day"))
        bot.send_message(chat_id, "📌 অনুগ্রহ করে একটি ক্যাটাগরি সিলেক্ট করুন:", reply_markup=markup)
        return

    elif message.text == button_labels["btn2"]:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💸 bKash Withdraw", callback_data="withdraw_bkash"))
        bot.send_message(chat_id, f"💰 আপনার বর্তমান ব্যালেন্স: {wallets.get(chat_id, 0.0)} BDT", reply_markup=markup)
        return

    elif message.text == button_labels["btn3"]:
        support_mode[chat_id] = True
        bot.send_message(chat_id, "📩 আপনার মেসেজটি নিচে লিখুন, অ্যাডমিন আপনাকে শীঘ্রই উত্তর দেবেন।")
        return

    # Support Mode
    if support_mode.get(chat_id):
        username = message.from_user.username
        username_str = f"@{username}" if username else "No username"
        bot.send_message(ADMIN_ID, f"📩 Support: {message.text}\nFrom ID: {chat_id}\nUsername: {username_str}")
        bot.send_message(chat_id, "✅ মেসেজটি পাঠানো হয়েছে।")
        support_mode[chat_id] = False
        return

    # Admin Deposit Approval
    if chat_id == ADMIN_ID and chat_id in pending_approvals:
        try:
            amount = float(message.text)
            target = pending_approvals[chat_id]
            wallets[target] = wallets.get(target, 0) + amount
            bot.send_message(target, f"✅ পেমেন্ট নিশ্চিত! {amount} টাকা যোগ হয়েছে।")
            del pending_approvals[chat_id]
            return
        except: bot.send_message(chat_id, "⚠️ ভুল সংখ্যা!")

    # User Input Logic
    if chat_id in users:
        data = users[chat_id]
        if data["step"] == "w_amount":
            try:
                amt = float(message.text)
                if amt > wallets.get(chat_id, 0):
                    bot.send_message(chat_id, "⚠️ আপনার পর্যাপ্ত ব্যালেন্স নেই।")
                    del users[chat_id]
                    return
                data["w_amount"] = amt
                data["step"] = "w_number"
                bot.send_message(chat_id, "📌 আপনার bKash নাম্বারটি দিন:")
            except: bot.send_message(chat_id, "⚠️ ভুল সংখ্যা!")
        
        elif data["step"] == "w_number":
            amt = data["w_amount"]
            number = message.text
            user = message.from_user.username or "N/A"
            admin_text = f"🚨 New bKash Withdrawal\nUser: @{user}\nAmount: {amt} BDT\nbKash Number: {number}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Paid", callback_data=f"wpay_{chat_id}_{amt}"), types.InlineKeyboardButton("❌ Deny", callback_data=f"wdeny_{chat_id}"))
            bot.send_message(ADMIN_ID, admin_text, reply_markup=markup)
            bot.send_message(chat_id, "✅ আপনার উইথড্র রিকোয়েস্টটি অ্যাডমিনের কাছে পাঠানো হয়েছে।")
            del users[chat_id]

        elif data["step"] == "part1":
            data["part1"] = message.text
            data["step"] = "part2"
            bot.send_message(chat_id, "📌 password লিস্ট দিন")
        elif data["step"] == "part2":
            data["part2"] = message.text
            data["step"] = "part3"
            bot.send_message(chat_id, "📌 2FA লিস্ট দিন")
        elif data["step"] == "part3":
            data["part3"] = message.text
            data["step"] = "bkash"
            bot.send_message(chat_id, "📌 bKash নাম্বার দিন")
        elif data["step"] == "bkash":
            data["bkash"] = message.text
            username = message.from_user.username
            username_str = f"@{username}" if username else "No username"
            admin_msg = (f"🔥 New Sell: {data['category']}\nUser ID: {chat_id}\nUsername: {username_str}\n\n1M: {data['part1']}\n2M: {data['part2']}\n2FA: {data['part3']}\nBKash: {data['bkash']}")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{chat_id}"), types.InlineKeyboardButton("❌ Deny", callback_data=f"deny_{chat_id}"))
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
            bot.send_message(chat_id, "✅ রিকোয়েস্ট পাঠানো হয়েছে।")
            del users[chat_id]

# =========================
# CALLBACK QUERY HANDLER
# =========================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("sell_"):
        chat_id = call.message.chat.id
        # ডাইনামিক বাটন নাম ব্যবহার করা হয়েছে
        category = button_labels["sell1"] if call.data == "sell_regular" else button_labels["sell2"]
        users[chat_id] = {"step": "part1", "category": category}
        bot.edit_message_text(f"📌 আপনি সিলেক্ট করেছেন: {category}\n\nএখন সিরিয়াল অনুযায়ী username লিস্ট দিন:", chat_id, call.message.message_id)
    elif call.data == "withdraw_bkash":
        users[call.message.chat.id] = {"step": "w_amount"}
        bot.edit_message_text("📌 কত টাকা উইথড্র করতে চান? (শুধুমাত্র সংখ্যা দিন):", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("approve_"):
        user_id = int(call.data.split("_")[1])
        pending_approvals[call.message.chat.id] = user_id
        bot.edit_message_text("✅ অনুমোদিত। ব্যালেন্স লিখুন:", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("deny_"):
        bot.send_message(int(call.data.split("_")[1]), "❌ দুঃখিত, আপনার রিকোয়েস্টটি রিজেক্ট করা হয়েছে।")
        bot.edit_message_text("❌ রিজেক্ট করা হয়েছে।", call.message.chat.id, call.message.message_id)
    elif call.data.startswith("wpay_"):
        _, uid, amt = call.data.split("_")
        wallets[int(uid)] = wallets.get(int(uid), 0) - float(amt)
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
