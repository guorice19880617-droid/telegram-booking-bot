# ===============================
# Flask 保活（Render 必须）
# ===============================
from flask import Flask
import threading
import os
from datetime import datetime

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
    "times": [],
    "deadline": None
}

booking_status = {}
chat_step = {}


# ===============================
# 工具函数
# ===============================
def split_text(text):
    return [x.strip() for x in text.replace("，", ",").split(",") if x.strip()]


# ===============================
# /start
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 预约机器人\n\n"
        "/create 创建预约表"
    )


# ===============================
# 创建排班（管理员）
# ===============================
async def create_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat = update.effective_chat
    user = update.effective_user

    admins = await context.bot.get_chat_administrators(chat.id)
    admin_ids = [a.user.id for a in admins]

    if user.id not in admin_ids:
        await update.message.reply_text("❌ 仅管理员可创建排班")
        return

    chat_step[chat.id] = "days"

    await update.message.reply_text(
        "请输入日期\n例如：周一,周二,周三"
    )


# ===============================
# 文本流程控制 ⭐⭐⭐⭐⭐
# ===============================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text
    chat_id = update.effective_chat.id

    step = chat_step.get(chat_id)

    # ========= 输入日期 =========
    if step == "days":

        schedule_config["days"] = split_text(text)

        chat_step[chat_id] = "times"

        await update.message.reply_text(
            "请输入时间段\n例如：8:00-9:00,9:00-10:00"
        )

        return

    # ========= 输入时间段 =========
    if step == "times":

        schedule_config["times"] = split_text(text)

        chat_step[chat_id] = "deadline"

        await update.message.reply_text(
            "请输入截止时间\n例如：2025-03-05 18:00"
        )

        return

    # ========= 输入截止时间 ⭐⭐⭐⭐⭐（最重要） =========
    if step == "deadline":

        schedule_config["deadline"] = text

        chat_step[chat_id] = None

        await show_panel(update)

        return


# ===============================
# 显示排班面板 ⭐⭐⭐⭐⭐
# ===============================
async def show_panel(update: Update):

    keyboard = [
        [InlineKeyboardButton(d, callback_data=f"day_{d}")]
        for d in schedule_config["days"]
    ]

    notice = """
📢 *预约公告*

本次预约截止时间为:
{deadline_text}

预约如未排满将自动解约，
待下次再预约。

如预约后未到场，将进入黑名单。

感谢理解 😊
"""

    await update.effective_chat.send_message(
        notice,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ===============================
# 按钮预约 ⭐⭐⭐⭐⭐
# ===============================
async def booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user.first_name
    data = query.data

    # ===== 选择日期 =====
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

    # ===== 预约时间 =====
    if data.startswith("book_"):

        # 检查截止时间
        if schedule_config["deadline"]:
            try:
                deadline_time = datetime.strptime(
                    schedule_config["deadline"],
                    "%Y-%m-%d %H:%M"
                )

                if datetime.now() > deadline_time:
                    await query.message.reply_text("❌ 预约已截止")
                    return

            except:
                pass

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

app_bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
app_bot.add_handler(CallbackQueryHandler(booking_callback))


# ===============================
# 启动 Bot
# ===============================
app_bot.run_polling()
