import http
import logging
import os
import time

from dotenv import load_dotenv
import requests
import telegram

load_dotenv()

PRACTICUM_TOKEN = os.getenv('YP_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('ID')

CONST_ERROR = 'Константа {const} пуста!'
STATUS_CHANGED = 'Изменился статус проверки работы "{name}". {verdict}'
RUNTIME_ERROR = ('Ошибка времени выполнения '
                 '{error} {params} {url} {headers} {value}')
NO_RESPONSE = 'Не получен ответ от сервера {error} {params} {url} {headers}'
INVALID_STATUS_CODE = 'Сервер возвращает неожиданный статус код {code}'
ERROR_MESSAGE = 'Сбой в работе программы: {error}'
MESSAGE = 'Обязательная переменная пуста!'
EMPTY_LIST = 'Получен пустой список: {error}'
UNKNOWN_STATUS = 'Неизвестный статус: {status}'

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
    try:
        payload = {'from_date': current_timestamp}
        request_params = dict(url=url, headers=HEADERS, params=payload)
        response = requests.get(**request_params)
    except requests.exceptions.RequestException as error:
        raise ConnectionError(NO_RESPONSE.format(
            error=error,
            **request_params
        ))

    for key in ('code', 'error'):
        if key in response.json():
            raise RuntimeError(RUNTIME_ERROR.format(
                error=key,
                **request_params,
                value=response.json()[key]
            ))
    if response.status_code != http.HTTPStatus.OK:
        raise ConnectionError(INVALID_STATUS_CODE.format(
            code=response.status_code
        ))
    json = response.json()
    return json


def parse_status(homework):
    """Проверяет корректность и изменения статуса, возвращает сообщение."""
    return STATUS_CHANGED.format(
        name=homework["homework_name"],
        verdict=HOMEWORK_STATUSES[homework['status']]
    )


def check_response(response):
    """Проверяет ответ на корректность и не изменился ли статус."""
    try:
        homework = response.get('homeworks')[0]
        status = homework["status"]
    except IndexError as error:
        raise IndexError(EMPTY_LIST.format(error=error))
    if status not in HOMEWORK_STATUSES:
        raise ValueError(UNKNOWN_STATUS.format(status=status))

    return homework


def main():
    """Основная функция."""
    for const in TOKENS:
        if TOKENS[const] is None:
            logging.critical(CONST_ERROR.format(const=const))
            raise ValueError(MESSAGE)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(ENDPOINT, current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)

        except Exception as error:
            logging.error(ERROR_MESSAGE.format(error=error))
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(__file__ + '.log')
        ],
        format='%(asctime)s, %(levelname)s, %(name)s, %(lineno)s, %(message)s,'
    )

    from unittest import TestCase, mock  # main as uni_main

    JSON = {'error': 'testing'}
    JSON_2 = {'homeworks': [{'homework_name': 'test', 'status': 'test'}]}
    JSON_3 = {'homeworks': 1}
    ReqEx = requests.RequestException

    class TestReq(TestCase):
        """Тесты страхующего кода."""

        @mock.patch('requests.get')
        def test_raised(self, rq_get):
            """Тест сбоя сети."""
            rq_get.side_effect = mock.Mock(side_effect=ReqEx('testing'))
            main()

        @mock.patch('requests.get')
        def test_error(self, rq_get):
            """
            Тесты: .
                JSON == отказ сервера.
                JSON_2 == неожиданный статус дз.
                JSON_3 == некорректный json.
            """
            resp = mock.Mock()
            resp.json = mock.Mock(return_value=JSON)
            rq_get.return_value = resp
            main()

    # uni_main()
    main()
