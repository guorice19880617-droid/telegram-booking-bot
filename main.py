# ===============================
# Flask 保活（Render 必须）
# ===============================
from flask import Flask
import threading
import os
import csv
from io import StringIO

ADMIN_ID = 5792653387

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
# 工具函数
# ===============================
def split_text(text):
    return [x.strip() for x in text.replace("，", ",").split(",") if x.strip()]


# ===============================
# start
# ===============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🤖 预约机器人已启动\n\n"
        "/create 创建预约表\n"
        "/list 查看预约表"
    )


# ===============================
# 创建预约
# ===============================
async def create_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    chat_step[chat_id] = "days"

    await update.message.reply_text(
        "请输入日期\n例如：周一,周二,周三"
    )


# ===============================
# 文本流程控制
# ===============================
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

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


    # 输入时间
    if step == "times":

        schedule_config["times"] = split_text(text)

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

    await update.message.reply_text(
        ANNOUNCEMENT,
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "✅ 预约表已生成\n点击日期预约",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ===============================
# 查看预约表
# ===============================
async def list_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not booking_status:

        await update.message.reply_text("当前没有预约记录")
        return

    text = "📋 当前预约表\n\n"

    for key, user in booking_status.items():

        day, t = key.split("_")

        text += f"{day} {t} — {user}\n"

    await update.message.reply_text(text)
# ===============================
# 导出预约表
# ===============================
async def export_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not booking_status:
        await update.message.reply_text("当前没有预约记录")
        return

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["日期", "时间", "用户"])

    for key, user in booking_status.items():
        day, t = key.split("_")
        writer.writerow([day, t, user])

    output.seek(0)

    await update.message.reply_document(
        document=output,
        filename="booking.csv",
        caption="📊 当前预约表"
    )
# ===============================
# 清空预约表（管理员）
# ===============================
async def clear_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ 只有管理员可以清空预约表")
        return

    booking_status.clear()

    await update.message.reply_text(
        "🧹 当前所有预约记录已清空"
    )
# ===============================
# 取消预约（管理员）
# ===============================
async def cancel_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.args:
        await update.message.reply_text(
            "用法：\n/cancel 周一 8:00-9:00"
        )
        return

    day = context.args[0]
    time = context.args[1]

    key = f"{day}_{time}"

    if key not in booking_status:

        await update.message.reply_text("该时间未被预约")
        return

    del booking_status[key]

    await update.message.reply_text(
        f"已取消 {day} {time} 的预约"
    )


# ===============================
# 按钮预约
# ===============================
async def booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user = query.from_user.first_name
    data = query.data

    # 点击日期
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


    # 点击时间
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


        # 判断是否全部约满
        total = len(schedule_config["days"]) * len(schedule_config["times"])

        if len(booking_status) == total:

            await query.message.reply_text(
                "🎉 所有时间段已预约完成！\n\n"
                "管理员发送 /list 查看预约表"
            )


# ===============================
# Handler 注册
# ===============================
app_bot.add_handler(CommandHandler("start", start))
app_bot.add_handler(CommandHandler("create", create_schedule))
app_bot.add_handler(CommandHandler("list", list_schedule))
app_bot.add_handler(CommandHandler("cancel", cancel_booking))
app_bot.add_handler(CommandHandler("clear", clear_schedule))
app_bot.add_handler(CommandHandler("export", export_schedule))

app_bot.add_handler(MessageHandler(filters.TEXT, text_handler))
app_bot.add_handler(CallbackQueryHandler(booking_callback))


# ===============================
# 启动 Bot
# ===============================
app_bot.run_polling()
