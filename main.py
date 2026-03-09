import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.environ.get("BOT_TOKEN")

# 预约配置
schedule_config = {
    "days": ["周一", "周二", "周三"],
    "times": ["10:00", "14:00", "16:00"]
}

# 公告
ANNOUNCEMENT = """
📢 预约公告

请选择下面时间进行预约
每人只能预约一次
预约满后管理员会查看预约表
"""

# 预约状态
booking_status = {}

# 已预约用户
user_booking = {}

# =============================
# Flask 保活（Render需要）
# =============================

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# =============================
# /start
# =============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = []

    for day in schedule_config["days"]:
        row = []
        for t in schedule_config["times"]:
            key = f"{day}-{t}"
            row.append(
                InlineKeyboardButton(
                    f"{day} {t}",
                    callback_data=key
                )
            )
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        ANNOUNCEMENT,
        reply_markup=reply_markup
    )


# =============================
# 点击预约
# =============================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user.full_name
    user_id = query.from_user.id

    key = query.data
    day, t = key.split("-")

    # 已预约
    if user_id in user_booking:
        await query.message.reply_text(
            "⚠️ 你已经预约过了，每人只能预约一次。"
        )
        return

    # 时间被占
    if key in booking_status:
        await query.message.reply_text(
            "❌ 该时间已经被预约。"
        )
        return

    # 预约成功
    booking_status[key] = user
    user_booking[user_id] = key

    await query.message.reply_text(
        f"✅ {user} 预约成功 {day} {t}"
    )

    # 判断是否全部约满
    total = len(schedule_config["days"]) * len(schedule_config["times"])

    if len(booking_status) == total:

        await query.message.reply_text(
            "🎉 所有时间段已经预约完成！\n\n"
            "管理员请发送 /list 查看完整预约表。"
        )


# =============================
# /list 查看预约表
# =============================

async def list_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = "📋 当前预约表\n\n"

    for day in schedule_config["days"]:
        text += f"{day}\n"

        for t in schedule_config["times"]:
            key = f"{day}-{t}"

            if key in booking_status:
                user = booking_status[key]
                text += f"{t}  ✅ {user}\n"
            else:
                text += f"{t}  ❌ 空\n"

        text += "\n"

    await update.message.reply_text(text)


# =============================
# 主程序
# =============================

def main():

    # 启动 Flask 保活
    threading.Thread(target=run_web).start()

    # Telegram Bot
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_booking))
    application.add_handler(CallbackQueryHandler(button))

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
