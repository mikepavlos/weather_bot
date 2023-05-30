import logging
import os
import pprint
from datetime import datetime
from math import ceil

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Filters, MessageHandler, Updater

load_dotenv()

APIKEY = os.getenv('APIKEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKEN_NAMES = ('APIKEY', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

WINDS = (
    'северный',
    'северо-восточный',
    'восточный',
    'юго-восточный',
    'южный',
    'юго-западный',
    'западный',
    'северозападный',
    'северный'
)

bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN)


def check_tokens():
    """Проверка токенов."""

    token_exists = True

    for token in TOKEN_NAMES:
        if not globals().get(token):
            token_exists = False
            logging.critical(
                f'Отсутствует переменная окружения {token}')

    return token_exists


def new_city(update, context):
    city = update.message.text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=get_weather(city)
    )


def get_weather(city):
    response = requests.get(
        f'http://api.openweathermap.org/data/2.5/weather'
        f'?q={city}&lang=ru&units=metric&appid={APIKEY}'
    )

    data = response.json()
    if data.get('cod') == '404':
        raise KeyError(f'Город {city} не нейден.')

    city = data['name']
    weather = data['weather'][0]['description']
    temp_min = round(data['main']['temp_min'])
    temp_max = round(data['main']['temp_max'])
    cur_temp = data['main']['temp']
    humidity = data['main']['humidity']
    pressure = ceil(data['main']['pressure'] / 1.333)
    wind = data['wind']['speed']
    direction = WINDS[int((data['wind']['deg'] % 360) / 45)]

    city_weather = (
        f'{datetime.now().strftime("%d.%m.%Y %H:%M")}\n'
        f'{city}\n'
        f'Погода: {temp_min}-{temp_max}°C, {weather}\n'
        f'Температура: {cur_temp}°C\n'
        f'Влажность: {humidity}%\n'
        f'Давление: {pressure} мм.рт.ст\n'
        f'Ветер: {direction}, {wind} м/с\n'
    )

    return city_weather


def main():
    if not check_tokens():
        raise SystemExit('Программа принудительно остановлена')

    bot.send_message(TELEGRAM_CHAT_ID, 'Какой город? Такая погода:)')
    updater.dispatcher.add_handler(MessageHandler(Filters.text, new_city))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
