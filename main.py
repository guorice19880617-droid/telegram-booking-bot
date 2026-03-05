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
