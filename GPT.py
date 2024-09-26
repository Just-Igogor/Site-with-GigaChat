import json
import requests
from flask import Flask

AUTHORIZATION = 'гAUTHORIZATION'
RqUID = 'гRqUID'

class GigaChat:
    # Инициализация класса GigaChat
    def __init__(self, auth, rq):
        self.auth = auth
        self.rqUID = rq
        self.get_token()
        self.communication = []

    # Получение токена
    def get_token(self):
        url = 'https://ngw.devices.sberbank.ru:9443/api/v2/oauth'
        headers = {
            'Authorization': f'Bearer {self.auth}',
            'RqUID': self.rqUID,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'scope': 'GIGACHAT_API_PERS'
        }
        response = self._post(url, headers, data)
        self.access_token = json.loads(response.text)["access_token"]

    # Обёртка для выполнения POST-запросов
    def _post(self, url, headers, data, verify=False, is_json=False):
        if is_json:
            return requests.post(url, headers=headers, json=data, verify=verify)
        else:
            return requests.post(url, headers=headers, data=data, verify=verify)

    # Метод для взаимодействия с GigaChat
    def ask_a_question(self, question, temperature=0.7):
        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",  # Исправлено значение заголовка
            "Authorization": f"Bearer {self.access_token}"
        }
        self.communication.append({"role": "user", "content": question})
        data = {
            "model": "GigaChat:latest",
            "messages": self.communication,
            "temperature": temperature
        }
        response = self._post(url, headers, data, is_json=True).json()
        content = response['choices'][0]['message']['content']
        self.communication.append({"role": "assistant", "content": content})
        return content

    # Сброс истории общения
    def reset(self):
        self.communication.clear()
