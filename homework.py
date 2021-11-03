import http
import logging
import os
import sys
import time

import requests
from dotenv import load_dotenv

import telegram

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('ID')

CONST_ERROR = 'Константа {const} пуста!'
STATUS_CHANGED = 'Изменился статус проверки работы "{name}". {verdict}'
INVALID_CERTIFICATE = 'Проблемы с SSL сертификатом сервера {error} {value}'
TIME_OUT = 'Сервер слишком долго не отвечает - таймаут {error} {value}'
NO_RESPONSE = 'Не получен ответ от сервера {error} {params} {url} {headers}'
INVALID_STATUS_CODE = 'Сервер возвращает неожиданный статус код {code}'

RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}
TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'CHAT_ID': CHAT_ID,
}


def send_message(bot, message):
    """Отправляет сообщение через бота."""
    bot.send_message(CHAT_ID, message)


def get_api_answer(url, current_timestamp):
    """Получает ответ API и проверяет его."""
    payload = {'from_date': current_timestamp}
    try:
        response = requests.get(url, headers=HEADERS, params=payload)
    except requests.exceptions.HTTPError as error:
        raise requests.exceptions.HTTPError(NO_RESPONSE.format(
            error=error,
            params=payload,
            url=url,
            headers=HEADERS
        ))
    cases = [
        ['code', INVALID_CERTIFICATE],
        ['error', TIME_OUT]
    ]
    for error, message in cases:
        if error in response.json():
            raise ValueError(message.format(
                error=error,
                value=response.json()[error]
            ))
    if response.status_code == http.HTTPStatus.OK:
        return response.json()
    raise ValueError(INVALID_STATUS_CODE.format(code=response.status_code))


def parse_status(homework):
    """Проверяет корректность и изменения статуса, возвращает сообщение."""
    status = homework['status']
    return STATUS_CHANGED.format(
        name=homework["homework_name"],
        verdict=HOMEWORK_STATUSES[status]
    )


def check_response(response):
    """Проверяет ответ на корректность и не изменился ли статус."""
    try:
        homework = response.get('homeworks')[0]
    except IndexError as error:
        message = f'Получен пустой список: {error}'
        logging.error(message)
        raise IndexError(message)

    if homework['status'] not in HOMEWORK_STATUSES:
        message = f'Неизвестный статус: {homework["status"]}'
        logging.error(message)
        raise ValueError(message)

    return homework


def main():
    """Основная функция."""
    for const in TOKENS:
        if TOKENS[const] is None:
            message = 'Обязательная переменная пуста!'
            logging.critical(CONST_ERROR.format(const=const))
            return sys.exit(message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            # homework = check_response(response)
            message = parse_status(response)
            send_message(bot, message)
            current_timestamp = response['current_date']
        except Exception as error:
            logging.error(f'Сбой в работе программы: {error}')
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(__file__ + '.log')
        ],
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s, %(lineno)s'
    )
    main()
