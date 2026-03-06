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

bot = ApplicationBuilder().token(BOT_TOKEN).build()


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
# 数据缓存
# ===============================
schedule = {
    "days": [],
    "times": []
}

booking = {}

user_booking = {}

blacklist = set()

chat_step = {}


# ===============================
# start
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 预约机器人已启动\n\n"
        "管理员使用 /create 创建预约表"
    )


# ===============================
# 创建预约
# ===============================
async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_step[update.message.chat_id] = "days"

    await update.message.reply_text(
        "请输入日期\n\n例：\n周一,周二,周三"
    )


# ===============================
# reset
# ===============================
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    booking.clear()
    user_booking.clear()

    await update.message.reply_text("✅ 预约已清空")


# ===============================
# 查看预约
# ===============================
async def list_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not booking:
        await update.message.reply_text("暂无预约")
        return

    text = "📋 当前预约\n\n"

    for k,v in booking.items():
        text += f"{k} ：{v}\n"

    await update.message.reply_text(text)


# ===============================
# 黑名单
# ===============================
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text("用法: /ban 用户ID")
        return

    uid = int(context.args[0])

    blacklist.add(uid)

    await update.message.reply_text("🚫 已加入黑名单")


# ===============================
# 文本流程
# ===============================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text
    chat_id = update.message.chat_id

    step = chat_step.get(chat_id)

    if step == "days":

        schedule["days"] = text.split(",")

        chat_step[chat_id] = "times"

        await update.message.reply_text(
            "请输入时间段\n\n例：\n8:00-9:00,9:00-10:00"
        )

        return


    if step == "times":

        schedule["times"] = text.split(",")

        chat_step[chat_id] = None

        await show_panel(update)

        return


# ===============================
# 显示预约
# ===============================
async def show_panel(update):

    keyboard = []

    for d in schedule["days"]:

        keyboard.append([
            InlineKeyboardButton(
                d,
                callback_data=f"day_{d}"
            )
        ])

    await update.message.reply_text(
        ANNOUNCEMENT,
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "📅 请选择预约日期",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ===============================
# 按钮点击
# ===============================
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user.first_name
    user_id = query.from_user.id
    data = query.data


    if user_id in blacklist:

        await query.message.reply_text("❌ 你已被禁止预约")
        return


    # 选择日期
    if data.startswith("day_"):

        day = data.split("_")[1]

        keyboard = []

        for t in schedule["times"]:

            key = f"{day}_{t}"

            name = booking.get(key)

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


        if key in booking:

            await query.message.reply_text(
                f"❌ 已被 {booking[key]} 预约"
            )

            return


        if user_id in user_booking:

            await query.message.reply_text(
                "❌ 你已经预约过"
            )

            return


        booking[key] = user

        user_booking[user_id] = key


        await query.message.reply_text(
            f"✅ {user} 预约成功\n\n{day} {t}"
        )


# ===============================
# Handler
# ===============================
bot.add_handler(CommandHandler("start", start))
bot.add_handler(CommandHandler("create", create))
bot.add_handler(CommandHandler("reset", reset))
bot.add_handler(CommandHandler("list", list_booking))
bot.add_handler(CommandHandler("ban", ban))

bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
bot.add_handler(CallbackQueryHandler(callback))


# ===============================
# 启动
# ===============================
bot.run_polling()
