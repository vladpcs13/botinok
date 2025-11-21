import telebot
from telebot import types
import google.generativeai as genai
from flask import Flask, request

TOKEN = "8386093867:AAFy_CAN7KeAUMqt04Ovbrxv82jeRh3UzN0"
GEMINI_KEY = "AIzaSyCYmmY1beGXe6aAT5lG36nNwATz2ZEp8jA"
ADMIN_ID = 7532828180

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Настройка Gemini
genai.configure(api_key=GEMINI_KEY)

# Храним историю чатов
history = {}
# Храним системный промпт
system_prompt = "Ты — дружелюбный AI-ассистент."


def get_gemini_response(user_id, message):
    """Отправка запроса к Gemini с историей сообщений"""
    if user_id not in history:
        history[user_id] = []

    # Добавляем сообщение пользователя в историю
    history[user_id].append({"role": "user", "content": message})

    # Подготавливаем контекст
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[user_id])

    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(
        messages,
        generation_config=genai.types.GenerationConfig(
            temperature=0.8,
            max_output_tokens=500
        )
    )

    # Ответ Gemini
    reply_text = response.text

    # Сохраняем в историю
    history[user_id].append({"role": "assistant", "content": reply_text})

    return reply_text


@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот с интеллектом Gemini. Задавай вопросы!")


@bot.message_handler(commands=['setprompt'])
def set_prompt(message):
    """Установка системного промпта (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "У вас нет доступа.")
        return

    prompt = message.text.replace("/setprompt", "").strip()

    if not prompt:
        bot.reply_to(message, "Напиши так: /setprompt <текст>")
        return

    global system_prompt
    system_prompt = prompt

    bot.reply_to(message, f"Промпт обновлён:\n\n{prompt}")


@bot.message_handler(func=lambda m: True)
def conversation(message):
    """Обычный диалог"""
    user_id = message.from_user.id
    reply = get_gemini_response(user_id, message.text)
    bot.send_message(message.chat.id, reply)


# --- Webhook routes for Render.com ---

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200


@app.route("/")
def home():
    return "Bot is running!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
