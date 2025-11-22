import telebot
from telebot import types
import yt_dlp
import os
import time
from flask import Flask
from telebot.apihelper import ApiTelegramException


TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)


def safe_send(method, *args, **kwargs):
    while True:
        try:
            return method(*args, **kwargs)
        except ApiTelegramException as e:
            if e.error_code == 429:
                wait = int(e.result_json["parameters"]["retry_after"])
                print(f"⚠ Rate limit: wait {wait} sec…")
                time.sleep(wait)
            else:
                raise


def progress_hook(d, chat_id, msg_id):
    if d['status'] == 'downloading':
        percent = d.get("_percent_str", "").replace("\x1b[0;94m", "").replace("\x1b[0m", "").strip()
        try:
            safe_send(
                bot.edit_message_text,
                chat_id=chat_id,
                message_id=msg_id,
                text=f"⏳ Загружаю: {percent}"
            )
        except:
            pass



def download(url, quality, chat_id, msg_id):
    ydl_opts = {
        "outtmpl": "download.%(ext)s",
        "progress_hooks": [lambda d: progress_hook(d, chat_id, msg_id)]
    }

    if quality == "audio":
        ydl_opts["format"] = "bestaudio/best"
    else:
        ydl_opts["format"] = f"bestvideo[height={quality}]+bestaudio/best/best"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename



@bot.message_handler(commands=['start'])
def start(message):
    safe_send(bot.send_message, message.chat.id, "Тебя тоже достало что нигде не можешь скачать видео или музыку? Кидай ссылку. Создатель @BannedThirdTimes")



@bot.message_handler(func=lambda m: m.text.startswith(("http://", "https://")))
def ask_quality(message):
    url = message.text.strip()

    ydl_opts = {"quiet": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    kb = types.InlineKeyboardMarkup()
    added = set()

    for f in info["formats"]:
        h = f.get("height")
        if h and h not in added:
            kb.add(types.InlineKeyboardButton(f"{h}p", callback_data=f"q{h}|{url}"))
            added.add(h)

    kb.add(types.InlineKeyboardButton("Аудио", callback_data=f"qaudio|{url}"))

    safe_send(bot.send_message, message.chat.id, "выбери:", reply_markup=kb)



@bot.callback_query_handler(func=lambda call: call.data.startswith("q"))
def process_callback(call):
    safe_send(bot.answer_callback_query, call.id)

    data, url = call.data[1:].split("|")

    if data == "audio":
        quality = "audio"
        display = "Аудио"
    else:
        quality = data
        display = f"{quality}p"

    msg = safe_send(bot.send_message, call.message.chat.id, f"⏳ Загрузка ({display})…")
    chat_id = call.message.chat.id
    msg_id = msg.message_id

    try:
        filename = download(url, quality, chat_id, msg_id)

        ext = filename.split(".")[-1]
        new_name = f"@Reuploader13Bot.{ext}"

        if os.path.exists(new_name):
            os.remove(new_name)

        os.rename(filename, new_name)

        safe_send(bot.edit_message_text, "Отправляю…", chat_id, msg_id)

        with open(new_name, "rb") as f:
            if quality == "audio":
                safe_send(bot.send_audio, chat_id, f)
            else:
                safe_send(bot.send_video, chat_id, f)

        os.remove(new_name)

    except Exception as e:
        safe_send(bot.send_message, chat_id, f"❌ Ошибка:\n{e}")


print("Created by @BannedThirdTimes")


# ----------------------------
# RUN ON RENDER
# ----------------------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running"


import threading
threading.Thread(target=lambda: bot.infinity_polling(skip_pending=True)).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
