import logging
import os
import sys
from datetime import datetime
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
from math import ceil

import requests
from dotenv import load_dotenv
from telegram import Bot
from telegram.ext import Filters, MessageHandler, Updater

import exceptions

load_dotenv()

APIKEY = os.getenv('APIKEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKEN_NAMES = ('APIKEY', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

ENDPOINT = 'https://api.openweathermap.org/data/2.5/weather'

WEATHER_LIST = 0
MERCURY_COL_COEFFICIENT = 1.333
FULL_CIRCLE = 360
WIND_SECTOR = 45
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


def check_tokens():
    """Проверка токенов."""

    token_exists = True

    for token in TOKEN_NAMES:
        if not globals().get(token):
            token_exists = False
            logging.critical(
                f'Отсутствует переменная окружения {token}')

    return token_exists


def get_api_answer(city):
    """Получение ответа от API OpenWeather."""

    params = {
        'q': city,
        'lang': 'ru',
        'units': 'metric',
        'appid': APIKEY,
    }

    try:
        response = requests.get(ENDPOINT, params=params)

    except requests.RequestException as err:
        raise exceptions.CityError(
            f'Ошибка запроса API: {err}, '
            f'Эндпоинт {ENDPOINT}, '
            f'Параметры запроса: {params}'
        ) from err

    if response.status_code != HTTPStatus.OK:
        raise exceptions.CityError(
            f'Город {city} не найден. '
            f'Эндпоинт {ENDPOINT}, '
            f'Параметры запроса: {params}, '
            f'Код ошибки {response.status_code}'
        )

    return response.json()


def check_response(response):
    """Валидация ответа API."""

    if not isinstance(response, dict):
        raise TypeError(
            f'Ожидается ответ типа <dict>, получен тип {type(response)}'
        )

    for key in ('weather', 'main', 'wind'):
        if key not in response:
            raise KeyError(f'В ответе отсутствует ключ <{key}>')

    weather_description = response['weather']
    if not isinstance(response['weather'], list):
        raise TypeError(
            f'Под ключом <weather> ожидается список <list>, '
            f'получен {type(weather_description)}'
        )

    return response


def parse_weather(data):
    """Получение данных погоды для города."""

    city = data['name']
    weather = data['weather'][WEATHER_LIST].get('description', 'нет данных')
    temp_min = round(data['main'].get('temp_min', 'нет данных'))
    temp_max = round(data['main'].get('temp_max', 'нет данных'))
    current_temp = data['main'].get('temp', 'нет данных')
    humidity = data['main'].get('humidity', 'нет данных')
    pressure = data['main'].get('pressure', 'нет данных')
    wind = data['wind'].get('speed', 'нет данных')
    direction = data['wind'].get('deg', 'нет данных')

    if isinstance(pressure, (int, float)):
        pressure = ceil(pressure / MERCURY_COL_COEFFICIENT)

    if isinstance(direction, (int, float)):
        direction = WINDS[int((direction % FULL_CIRCLE) / WIND_SECTOR)]

    return (
        f'{datetime.now().strftime("%d.%m.%Y %H:%M")}\n'
        f'{city}\n'
        f'Погода: {temp_min}-{temp_max}°C, {weather}\n'
        f'Температура: {current_temp}°C\n'
        f'Влажность: {humidity}%\n'
        f'Давление: {pressure} мм.рт.ст\n'
        f'Ветер: {direction}, {wind} м/с\n'
    )


def send_message(bot, message='Город, пожалуйста.'):
    """Отправка сообщения в чат Telegram."""

    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Сообщение отправлено в Telegram: {message}')

    except Exception as err:
        raise exceptions.SendMessageFailure(
            f'Сообщение не отправлено. '
            f'Ошибка обращения к API Telegram. {err}, '
            f'id чата: {TELEGRAM_CHAT_ID}'
        )


def main(update, _):
    """Основной блок, вызывает блоки программы, обрабатывает исключения."""

    city = update.message.text

    try:
        response = get_api_answer(city)
        weather = check_response(response)
        message = parse_weather(weather)
        send_message(bot, message)

    except Exception as err:
        message = f'Ой-ой: {err}'
        send_message(bot, message)
        logging.error(message)


if __name__ == '__main__':

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s '
               '[%(levelname)s] '
               '%(funcName)s, '
               '%(lineno)d: '
               '%(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(
                filename=os.path.join(
                    os.path.dirname(__file__),
                    'program.log'),
                mode='w',
                maxBytes=5000000,
                backupCount=5,
                encoding='utf-8',
            )
        ]
    )

    if not check_tokens():
        raise SystemExit('Программа принудительно остановлена')

    bot = Bot(token=TELEGRAM_TOKEN)
    updater = Updater(token=TELEGRAM_TOKEN)

    send_message(bot, 'Привет! Напиши город, пожалуйста.')

    updater.dispatcher.add_handler(MessageHandler(Filters.text, main))
    updater.start_polling()
    updater.idle()
