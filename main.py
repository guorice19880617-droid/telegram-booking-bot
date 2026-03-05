# ===============================
# Flask 保活（Render 必须）
# ===============================
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()


# ===============================
# Telegram Bot
# ===============================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# ⭐ 只创建一次 Bot
app_bot = ApplicationBuilder().token(BOT_TOKEN).build()


# ===============================
# 状态缓存（群聊专用 ⭐⭐⭐⭐⭐）
# ===============================
schedule_config = {
    "days": [],
    "times": []
}

booking_status = {}

# ⭐ 群聊步骤记录
chat_step = {}


# ===============================
# start
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 机器人已启动\n\n"
        "使用 /create 创建预约表"
    )


# ===============================
# 创建排班
# ===============================
async def create_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_step[update.message.chat_id] = "days"

    await update.message.reply_text(
        "请输入日期（例如：周一,周二,周三）"
    )


# ===============================
# 文本流程控制 ⭐⭐⭐⭐⭐
# ===============================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    chat_id = update.message.chat_id

    step = chat_step.get(chat_id)

    # 输入日期
    if step == "days":

        schedule_config["days"] = text.split(",")
        chat_step[chat_id] = "times"

        await update.message.reply_text(
            "请输入时间段（例如：8:00-9:00,9:00-10:00）"
        )
        return

    # 输入时间段
   if step == "times":

    schedule_config["times"] = text.split(",")
    chat_step[chat_id] = None

    # ⭐ 直接生成日期按钮
    keyboard = []

    for d in schedule_config["days"]:
        keyboard.append([
            InlineKeyboardButton(d, callback_data=f"day_{d}")
        ])

    await update.message.reply_text(
        "✅ 预约表已生成\n点击日期开始预约",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return


# ===============================
# 显示预约面板
# ===============================
async def show_panel(update):

    keyboard = []

    for d in schedule_config["days"]:
        keyboard.append([
            InlineKeyboardButton(d, callback_data=f"day_{d}")
        ])

    await update.message.reply_text(
        "✅ 预约表已生成\n点击日期开始预约",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ===============================
# 按钮点击预约
# ===============================
async def booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user.first_name
    data = query.data

    # 选择日期
    if data.startswith("day_"):

        day = data.split("_")[1]

        keyboard = []

        for t in schedule_config["times"]:
            key = f"{day}_{t}"
            name = booking_status.get(key)

            text = f"{t} ({name})" if name else t

            keyboard.append([
                InlineKeyboardButton(
                    text,
                    callback_data=f"book_{day}_{t}"
                )
            ])

        await query.message.reply_text(
            f"{day} 选择时间",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # 预约时间
    if data.startswith("book_"):

        _, day, t = data.split("_")
        key = f"{day}_{t}"

        if key in booking_status:
            await query.message.reply_text(
                f"❌ 已被 {booking_status[key]} 预约"
            )
            return

        booking_status[key] = user

        await query.message.reply_text(
            f"✅ {user} 预约成功 {day} {t}"
        )


# ===============================
# Handler 注册 ⭐⭐⭐⭐⭐
# ===============================
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("create", create_schedule))

app_bot.add_handler(MessageHandler(filters.TEXT, text_handler))
app_bot.add_handler(CallbackQueryHandler(booking_callback))


# ===============================
# 启动 Bot
# ===============================
app_bot.run_polling()
