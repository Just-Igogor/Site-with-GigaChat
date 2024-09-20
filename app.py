import csv
import os
import requests
from flask import Flask, render_template, request, redirect, url_for, jsonify
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from gigachat import GigaChat

app = Flask(__name__)

# Инициализируем GigaChat
AUTHORIZATION = 'uAUTHORIZATION' 
RqUID = 'uRqUID'  # Уникальный идентификатор запроса
 
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

giga_chat = GigaChat(AUTHORIZATION, RqUID)

# Путь к файлу с тестами (CSV)
TESTS_FILE = 'tests.csv'

# Чтение данных теста из CSV
def read_tests():
    if not os.path.exists(TESTS_FILE):
        return []
    
    tests = []
    with open(TESTS_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:  # Убедимся, что строка имеет минимум 4 элемента (ID, название, хотя бы один вопрос и ответ)
                # Распакуем строки на базовые поля
                test_id = int(row[0])
                test_name = row[1]
                questions = row[2::2]  # Четные значения — вопросы
                answers = row[3::2]    # Нечетные значения — ответы
                tests.append({
                    'id': test_id,
                    'name': test_name,
                    'questions': questions,
                    'answers': answers
                })
            else:
                print(f"Ошибка в формате строки: {row}")  # Отладочный вывод на случай проблемы с CSV
    return tests

# Запись данных теста в CSV
def write_tests(tests):
    with open(TESTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for test in tests:
            row = [test['id'], test['name']]
            for question, answer in zip(test['questions'], test['answers']):
                row.extend([question, answer])
            writer.writerow(row)

# Главная страница — список тестов
@app.route('/')
def index():
    tests = read_tests()
    return render_template('index.html', tests=tests)

# Создание или редактирование теста
@app.route('/edit_test/<int:test_id>', methods=['GET', 'POST'])
def edit_test(test_id):
    tests = read_tests()

    if request.method == 'POST':
        test_name = request.form.get('test_name')
        questions = request.form.getlist('questions')
        answers = request.form.getlist('answers')

        if test_id == 0:  # Новый тест
            test_id = len(tests) + 1
            tests.append({
                'id': test_id,
                'name': test_name,
                'questions': questions,
                'answers': answers
            })
        else:  # Редактирование существующего
            for test in tests:
                if test['id'] == test_id:
                    test['name'] = test_name
                    test['questions'] = questions
                    test['answers'] = answers
                    break
        
        write_tests(tests)
        return redirect(url_for('index'))

    # Если GET-запрос, то открываем форму для редактирования
    if test_id > 0:
        test = next((test for test in tests if test['id'] == test_id), None)
    else:
        test = {'id': 0, 'name': '', 'questions': [], 'answers': []}
    
    return render_template('edit_test.html', test=test)

# Прохождение теста
@app.route('/take_test/<int:test_id>', methods=['GET', 'POST'])
def take_test(test_id):
    tests = read_tests()
    test = next((test for test in tests if test['id'] == test_id), None)
    
    if not test:
        print(f"Тест с id {test_id} не найден")  # Отладочный вывод
        return "Тест не найден", 404

    if request.method == 'POST':
        user_answers = request.form.getlist('user_answers')
        correct_answers = test['answers']

        scores = []
        for question, user_answer, correct_answer in zip(test['questions'], user_answers, correct_answers):
            # Формируем вопрос для GigaChat
            question_text = f"Сравните ответ пользователя: '{user_answer}' с правильным ответом: '{correct_answer}' на вопрос: '{question}'. И поставьте оценку от 0 до 100. ТЫ МОЖЕШЬ ОТВЕЧАТЬ ТОЛЬКО ЧИСЛОМ ОЦЕНКИ, КОТОРУЮ ТЫ ПОСТАВИЛ."
            score = giga_chat.ask_a_question(question_text)
            scores.append(score)
        
        average_score = sum(float(score) for score in scores) / len(scores)  # Предполагается, что GigaChat возвращает числовые оценки
        return render_template('test_result.html', test=test, user_answers=user_answers, scores=scores, average_score=average_score)

    return render_template('take_test.html', test=test)

if __name__ == '__main__':
    app.run(debug=True)
