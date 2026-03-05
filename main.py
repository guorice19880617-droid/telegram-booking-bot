import logging
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ====== 在这里填写你的信息 ======
import os BOT_TOKEN = os.getenv("8386805229:AAFzJoEXLVnwqcMICr6Id4zwkPluibILhXE")
CHANNEL_ID = -1000000000000  # 先随便写，后面我们再改成真实ID
ADMIN_ID = 123456789  # 填写你的Telegram数字ID
# =================================

logging.basicConfig(level=logging.INFO)

appointments = {}
create_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("输入 /create 创建预约")

async def create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    create_state["step"] = "title"
    await update.message.reply_text("请输入预约标题：")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if "step" not in create_state:
        return

    step = create_state["step"]

    if step == "title":
        create_state["title"] = update.message.text
        create_state["step"] = "slots"
        await update.message.reply_text("请输入时间段，每行一个，例如：\n周一 08:00-09:00")

    elif step == "slots":
        lines = update.message.text.split("\n")
        create_state["slots"] = {line.strip(): None for line in lines}
        create_state["step"] = "deadline"
        await update.message.reply_text("请输入截止时间，例如：2026-03-10 18:00")

    elif step == "deadline":
        create_state["deadline"] = update.message.text
        await publish(context)
        create_state.clear()
        await update.message.reply_text("预约已发布")

async def publish(context):
    title = create_state["title"]
    slots = create_state["slots"]
    deadline = create_state["deadline"]

    appointments["data"] = {
        "title": title,
        "slots": slots,
        "deadline": deadline
    }

    keyboard = []
    for slot in slots:
        keyboard.append([
            InlineKeyboardButton(f"{slot}（空）", callback_data=slot)
        ])

    text = f"📅 {title}\n\n⏰ 截止时间：{deadline}\n\n⚠ 每个时间段仅限1人\n"

    await context.bot.send_message(
        chat_id=CHANNEL_ID,
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = appointments.get("data")
    if not data:
        return

    slot = query.data

    deadline = datetime.strptime(data["deadline"], "%Y-%m-%d %H:%M")
    if datetime.now() > deadline:
        await query.answer("预约已截止", show_alert=True)
        return

    if data["slots"][slot] is None:
        name = query.from_user.username
        if not name:
            name = query.from_user.first_name

        data["slots"][slot] = name

        new_keyboard = []
        for s in data["slots"]:
            display_name = data["slots"][s] or "空"
            new_keyboard.append([
                InlineKeyboardButton(f"{s}（{display_name}）", callback_data=s)
            ])

        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(new_keyboard)
        )
    else:
        await query.answer("该时间段已被预约", show_alert=True)

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("create", create))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button))

app.run_polling()
