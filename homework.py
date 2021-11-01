import http
import logging
import os
import time
import requests
import telegram

from telegram.ext import Updater
from dotenv import load_dotenv


logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.StreamHandler(), logging.FileHandler('main.log')],
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('ID')

MESSAGE = 'Обязательная переменная пуста!'
if not PRACTICUM_TOKEN:
    logging.critical(MESSAGE)
if not TELEGRAM_TOKEN:
    logging.critical(MESSAGE)
if not CHAT_ID:
    logging.critical(MESSAGE)


BOT = telegram.Bot(token=TELEGRAM_TOKEN)

RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}


def send_message(bot, message):
    """Отправляет сообщение через бота."""
    bot.send_message(CHAT_ID, message)


def get_api_answer(url, current_timestamp):
    """Получает ответ API и проверяет его."""
    headers = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=headers, params=payload)
        if response.status_code != http.HTTPStatus.OK:
            logging.error('Код подключения к API != 200')
            raise requests.HTTPError
        return response.json()
    except requests.exceptions.SSLError as error:
        logging.error(f'Не безопасное подключение! {error}')


def parse_status(homework):
    """Проверяет корректность и изменения статуса, возвращает сообщение."""
    keys = ['status', 'homework_name']
    for key in keys:
        if key not in homework:
            message = f'Ключа {key} нет в ответе API'
            logging.error(message)
            raise KeyError(message)
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Неизвестный статус домашней работы.'
        logging.error(message)
        raise KeyError(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_response(response):
    """Проверяет ответ на корректность и не изменился ли статус."""
    try:
        homework = response.get('homeworks')[0]
    except IndexError as error:
        message = f'Получен пустой список: {error}'
        logging.error(message)
        send_message(BOT, message)

    if homework['status'] not in HOMEWORK_STATUSES:
        message = f'Неизвестный статус: {homework["status"]}'
        logging.error(message)
        raise Exception(message)

    return homework


def main():
    """Основная функция."""
    current_timestamp = int(time.time())
    BOT.send_message(CHAT_ID, 'Бот запущен.')
    updater = Updater(token=TELEGRAM_TOKEN)
    updater.start_polling()
    updater.idle()
    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(BOT, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            print(message)
            time.sleep(RETRY_TIME)
            continue


if __name__ == '__main__':
    main()
