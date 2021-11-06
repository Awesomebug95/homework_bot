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

CONST_ERROR = 'Ошибка! обязательная переменная: {const} пуста!'
STATUS_CHANGED = 'Изменился статус проверки работы "{name}". {verdict}'
CERTIFICATE_OR_TIME_FAIL = ('Ошибка времени выполнения '
                            '{error} {params} {url} {headers} {value}')
NO_RESPONSE = ('Не получен ответ от сервера, ошибка: {error}'
               'параметры запроса: {params} {url} {headers}')
UNSUITABLE_STATUS_CODE = ('Сервер возвращает неожиданный статус код {code},'
                          'параметры запроса: {params} {url} {headers}')
ERROR_MESSAGE = 'Сбой в работе программы: {error}'
EMPTY_CONST = 'Обязательная переменная пуста!'
EMPTY_LIST = 'Получен пустой список: {error}'
UNKNOWN_STATUS = 'Неизвестный статус: {status}'

RETRY_TIME = 300
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'

HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена, в ней нашлись ошибки.'
}
TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'CHAT_ID')


def send_message(bot, message):
    """Отправляет сообщение через бота."""
    bot.send_message(CHAT_ID, message)


def get_api_answer(url, current_timestamp):
    """Получает ответ API и проверяет его."""
    request_params = dict(
        url=url,
        headers=HEADERS,
        params={'from_date': current_timestamp}
    )
    try:
        response = requests.get(**request_params)
        response_json = response.json()
    except requests.exceptions.RequestException as error:
        raise ConnectionError(NO_RESPONSE.format(
            error=error,
            **request_params
        ))

    for key in ('code', 'error'):
        if key in response_json:
            raise RuntimeError(CERTIFICATE_OR_TIME_FAIL.format(
                error=key,
                **request_params,
                value=response_json[key]
            ))
    if response.status_code != http.HTTPStatus.OK:
        raise RuntimeError(UNSUITABLE_STATUS_CODE.format(
            code=response.status_code,
            **request_params
        ))
    return response_json


def parse_status(homework):
    """Возвращает сообщение с изменившимся статусом дз."""
    return STATUS_CHANGED.format(
        name=homework["homework_name"],
        verdict=HOMEWORK_VERDICTS[homework['status']]
    )


def check_response(response):
    """Проверяет ответ на корректность."""
    homework = response['homeworks'][0]
    if homework["status"] not in HOMEWORK_VERDICTS:
        raise ValueError(UNKNOWN_STATUS.format(status=homework["status"]))

    return homework


def main():
    """Основная функция."""
    for const in TOKENS:
        if globals()[const] is None:
            logging.critical(CONST_ERROR.format(const=const))
            raise ValueError(EMPTY_CONST)
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

    main()
