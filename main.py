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
# 数据缓存
# ===============================
schedule_config = {
    "days": [],
    "times": []
}

booking_status = {}

chat_step = {}


# ===============================
# 公告
# ===============================
ANNOUNCEMENT = """
📢 *预约公告*

本次预约如未排满将自动解约  
待下次再预约。

如预约后未到场，将进入黑名单。

感谢理解 😊
"""


# ===============================
# /start
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 预约机器人\n\n"
        "管理员使用 /create 创建预约表\n"
        "使用 /list 查看预约表"
    )


# ===============================
# /create
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

    # 输入时间
    if step == "times":

        schedule_config["times"] = text.replace("，", ",").split(",")

        chat_step[chat_id] = None

        await show_panel(update)

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
        ANNOUNCEMENT,
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ 预约表已生成\n点击日期预约",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ===============================
# 按钮处理
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

    # 预约
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

        # 判断是否全部预约完
        total = len(schedule_config["days"]) * len(schedule_config["times"])

        if len(booking_status) == total:

            await query.message.reply_text(
                "🎉 所有时间段已预约完成\n\n管理员输入 /list 查看预约表"
            )


# ===============================
# 查看预约表
# ===============================
async def list_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = "📋 当前预约表\n\n"

    for d in schedule_config["days"]:

        text += f"{d}\n"

        for t in schedule_config["times"]:

            key = f"{d}_{t}"

            name = booking_status.get(key, "空")

            text += f"{t}  {name}\n"

        text += "\n"

    await update.message.reply_text(text)


# ===============================
# Handler 注册
# ===============================
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("create", create_schedule))
app_bot.add_handler(CommandHandler("list", list_schedule))

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
