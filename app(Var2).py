from flask import Flask, render_template, request, redirect, url_for, jsonify, json
import requests
import csv
import os
from gigachat import GigaChat  # Подключаем наш класс
from requests.packages.urllib3.exceptions import InsecureRequestWarning

app = Flask(__name__)

# Инициализируем GigaChat
AUTHORIZATION = 'NjU0YzUyYmQtOWVlNC00ZmQ5LWIyMmQtMjA5Y2Q5ZDQ1OWViOmVmYjBhNWUzLTBhMjAtNDljOC05MTQxLWM4MGE5ODk1NjljMA==' 
RqUID = 'efb0a5e3-0a20-49c8-9141-c80a989569c0'  # Уникальный идентификатор запроса
 
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)



chat = GigaChat(AUTHORIZATION, RqUID)
# Путь к файлу CSV
CSV_FILE = 'tests.csv'

# Чтение тестов из JSON файла
def read_tests():
    if not os.path.exists('tests.json') or os.stat('tests.json').st_size == 0:
        return []
    
    try:
        with open('tests.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Ошибка декодирования JSON.")
        return []

# Запись тестов в JSON файл
def write_tests(tests):
    with open('tests.json', 'w', encoding='utf-8') as f:
        json.dump(tests, f, ensure_ascii=False, indent=4)

# Главная страница
@app.route('/')
def index():
    tests = read_tests()
    return render_template('index.html', tests=tests)



# Создание теста
@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        test_name = request.form['test_name']
        questions = request.form.getlist('questions')
        answers = request.form.getlist('answers')

        # Сохраняем тест в CSV файл
        with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for question, answer in zip(questions, answers):
                writer.writerow([test_name, question, answer])

        # Сохранение теста в JSON файл
        tests = read_tests()
        test_id = len(tests) + 1  # Генерируем уникальный ID для теста
        test_data = {
            'id': test_id,
            'name': test_name,
            'questions': questions,
            'answers': answers
        }
        tests.append(test_data)
        write_tests(tests)

        return redirect(url_for('index'))  # Перенаправление на главную страницу

    return render_template('create.html')


# Прохождение теста
@app.route('/test/<int:test_id>', methods=['GET', 'POST'])
def test(test_id):
    tests = read_tests()
    test = next((t for t in tests if t['id'] == test_id), None)
    
    if not test:
        return "Тест не найден", 404

    if request.method == 'POST':
        user_answers = request.form.getlist('answers')
        correct_answers = test['answers']
        score = 0
        
        # Использование GigaChat для сравнения ответов
        chat = GigaChat(auth="YOUR_AUTH_TOKEN", rq="YOUR_RQUID")
        
        for user_answer, correct_answer in zip(user_answers, correct_answers):
            similarity = chat.ask_a_question(f"Насколько ответ '{user_answer}' похож на '{correct_answer}'?")
            print(f"Ответ: {similarity}")  # Логгируем результат для отладки
            if "похож" in similarity.lower():  # Условие для определения сходства
                score += 1
        
        return render_template('result.html', score=score, total=len(correct_answers))

    return render_template('test.html', test=test)

# Страница с результатами
@app.route('/test/<int:test_id>/result', methods=['POST'])
def result(test_id):
    tests = read_tests()
    test = next((t for t in tests if t['id'] == test_id), None)
    
    if not test:
        return "Тест не найден", 404
    
    user_answers = request.form.getlist('answers')
    correct_answers = test['answers']
    score = 0
    
    for user_answer, correct_answer in zip(user_answers, correct_answers):
        if user_answer.strip().lower() == correct_answer.strip().lower():
            score += 1

    return render_template('result.html', score=score, total=len(correct_answers))

if __name__ == '__main__':
    app.run(debug=True)
