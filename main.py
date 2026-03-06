# ===============================
# Flask 保活（Render）
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
panel_message_id = {}


# ===============================
# 工具函数
# ===============================
def split_text(text):
    return [x.strip() for x in text.replace("，", ",").split(",") if x.strip()]


# ===============================
# start
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 排班机器人\n\n"
        "/create 创建排班表"
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
# 文本流程控制
# ===============================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    text = update.message.text
    chat_id = update.effective_chat.id

    step = chat_step.get(chat_id)

    # 输入日期
    if step == "days":

        schedule_config["days"] = split_text(text)

        chat_step[chat_id] = "times"

        await update.message.reply_text(
            "请输入时间段\n例如：8:00-9:00,9:00-10:00"
        )

        return

    # 输入时间段
    if step == "times":

        schedule_config["times"] = split_text(text)

        chat_step[chat_id] = None

        await show_panel(update)

        return


# ===============================
# 显示排班面板（顶级体验 ⭐⭐⭐⭐⭐）
# ===============================
async def show_panel(update: Update):

    chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton(d, callback_data=f"day_{d}")]
        for d in schedule_config["days"]
    ]

    msg = await update.message.reply_text(
        "✅ 排班表已生成\n点击日期预约",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    panel_message_id[chat_id] = msg.message_id


# ===============================
# 按钮预约
# ===============================
async def booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user.first_name
    data = query.data
    chat_id = query.message.chat_id

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

app_bot.add_handler(MessageHandler(filters.TEXT, text_handler))
app_bot.add_handler(CallbackQueryHandler(booking_callback))


# ===============================
# 启动
# ===============================
app_bot.run_polling()
