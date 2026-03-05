from flask import Flask
import threading
import os

# -------- Flask 端口（给 Render 检测用）--------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# -------- Telegram Bot --------
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("机器人已启动")

app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
app_bot.add_handler(CommandHandler("start", start))

app_bot.run_polling()

#----------
# 预约表配置
schedule_config = {
    "days": [],
    "times": []
}

# 预约状态
booking_status = {}

#---------------
async def create_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "请输入日期（例如：周一,周二,周三）"
    )

    context.user_data["step"] = "days"

#----------
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    if context.user_data.get("step") == "days":
        schedule_config["days"] = text.split(",")
        context.user_data["step"] = "times"

        await update.message.reply_text(
            "请输入时间段（例如：8:00-9:00,9:00-10:00）"
        )
        return

    if context.user_data.get("step") == "times":
        schedule_config["times"] = text.split(",")
        context.user_data["step"] = None

        await show_panel(update)
        return

#--------
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

#-----------
async def booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user.first_name
    data = query.data

    if data.startswith("day_"):
        day = data.split("_")[1]

        keyboard = []

        for t in schedule_config["times"]:
            key = f"{day}_{t}"
            name = booking_status.get(key)

            text = f"{t} ({name})" if name else t

            keyboard.append([
                InlineKeyboardButton(text, callback_data=f"book_{day}_{t}")
            ])

        await query.message.reply_text(
            f"{day} 选择时间",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

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

#--------
app_bot.add_handler(CommandHandler("create", create_schedule))
app_bot.add_handler(MessageHandler(filters.TEXT, text_handler))
app_bot.add_handler(CallbackQueryHandler(booking_callback))

