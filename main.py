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

app_bot = ApplicationBuilder().token(BOT_TOKEN).build()


# ===============================
# 公告内容
# ===============================
NOTICE = """
📢 预约公告

本次预约如未排满将自动解约
待下次再预约。

如预约后未到场，将进入黑名单。

感谢理解 😊
"""


# ===============================
# 数据缓存
# ===============================
schedule_config = {
    "days": [],
    "times": []
}

booking_status = {}

chat_step = {}


# ===============================
# start
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 预约机器人\n\n管理员输入 /create 创建预约表"
    )


# ===============================
# 创建预约
# ===============================
async def create_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_step[update.effective_chat.id] = "days"

    await update.message.reply_text(
        "请输入日期\n例如：周一,周二,周三"
    )


# ===============================
# 文本流程
# ===============================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text
    chat_id = update.effective_chat.id

    step = chat_step.get(chat_id)

    # 输入日期
    if step == "days":

        schedule_config["days"] = text.replace("，", ",").split(",")

        chat_step[chat_id] = "times"

        await update.message.reply_text(
            "请输入时间段\n例如：8:00-9:00,9:00-10:00"
        )

        return

    # 输入时间段
    if step == "times":

        schedule_config["times"] = text.replace("，", ",").split(",")

        chat_step[chat_id] = None

        await show_panel(update)

        return


# ===============================
# 显示预约面板
# ===============================
async def show_panel(update: Update):

    keyboard = []

    for d in schedule_config["days"]:
        keyboard.append([
            InlineKeyboardButton(d, callback_data=f"day_{d}")
        ])

    message = NOTICE + "\n\n📅 预约表\n点击日期开始预约"

    await update.effective_chat.send_message(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ===============================
# 按钮点击
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
            f"✅ {user} 预约成功\n{day} {t}"
        )


# ===============================
# Handler 注册
# ===============================
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("create", create_schedule))

app_bot.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        text_handler
    )
)

app_bot.add_handler(
    CallbackQueryHandler(booking_callback)
)


# ===============================
# 启动
# ===============================
app_bot.run_polling()
