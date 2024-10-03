import csv
import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from GPT import GigaChat

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Инициализируем GigaChat
AUTHORIZATION = 'NjU0YzUyYmQtOWVlNC00ZmQ5LWIyMmQtMjA5Y2Q5ZDQ1OWViOmVmYjBhNWUzLTBhMjAtNDljOC05MTQxLWM4MGE5ODk1NjljMA=='
RqUID = 'efb0a5e3-0a20-49c8-9141-c80a989569c0'
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

giga_chat = GigaChat(auth=AUTHORIZATION, rq=RqUID)

# Путь к файлу с тестами и пользователями (CSV)
TESTS_FILE = 'tests.csv'
USERS_FILE = 'users.csv'
# Путь к файлу с результатами
RESULTS_FILE = 'results.csv'
SECRET_ADMIN_PASSWORD = 'secret123'  # Секретный пароль для роли администратора

# Сохранение результатов теста
def save_test_result(username, test_name, question, user_answer, score, explanation):
    with open(RESULTS_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([username, test_name, question, user_answer, score, explanation])

# Чтение данных тестов из CSV
def read_tests():
    if not os.path.exists(TESTS_FILE):
        return []

    tests = []
    with open(TESTS_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 4:
                test_id = int(row[0])
                test_name = row[1]
                questions = row[2::2]
                answers = row[3::2]
                tests.append({
                    'id': test_id,
                    'name': test_name,
                    'questions': questions,
                    'answers': answers
                })
            else:
                print(f"Ошибка в формате строки: {row}")
    return tests

# Запись данных тестов в CSV
def write_tests(tests):
    with open(TESTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for test in tests:
            row = [test['id'], test['name']]
            for question, answer in zip(test['questions'], test['answers']):
                row.extend([question, answer])
            writer.writerow(row)

# Чтение данных пользователей из CSV
def read_users():
    if not os.path.exists(USERS_FILE):
        return []
    
    users = []
    with open(USERS_FILE, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) == 3:
                users.append({
                    'username': row[0],
                    'password': row[1],
                    'role': row[2]
                })
    return users

# Запись пользователей в CSV
def write_users(users):
    with open(USERS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for user in users:
            writer.writerow([user['username'], user['password'], user['role']])

# Декораторы для проверки авторизации и роли
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            return "Доступ запрещен"
        return f(*args, **kwargs)
    return decorated_function

# Главная страница — список тестов
@app.route('/')
@login_required
def index():
    tests = read_tests()
    return render_template('index.html', tests=tests)

# Создание или редактирование теста
@app.route('/edit_test/<int:test_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_test(test_id):
    tests = read_tests()

    if request.method == 'POST':
        test_name = request.form.get('test_name')
        questions = request.form.getlist('questions')
        answers = request.form.getlist('answers')

        if test_id == 0:
            test_id = len(tests) + 1
            tests.append({
                'id': test_id,
                'name': test_name,
                'questions': questions,
                'answers': answers
            })
        else:
            for test in tests:
                if test['id'] == test_id:
                    test['name'] = test_name
                    test['questions'] = questions
                    test['answers'] = answers
                    break

        write_tests(tests)
        return redirect(url_for('index'))

    test = next((test for test in tests if test['id'] == test_id), {'id': 0, 'name': '', 'questions': [], 'answers': []})
    return render_template('edit_test.html', test=test)

# Удаление теста
@app.route('/delete_test/<int:test_id>', methods=['POST'])
@login_required
@admin_required
def delete_test(test_id):
    tests = read_tests()
    tests = [test for test in tests if test['id'] != test_id]
    write_tests(tests)
    return redirect(url_for('index'))

# Прохождение теста
@app.route('/take_test/<int:test_id>', methods=['GET', 'POST'])
@login_required
def take_test(test_id):
    tests = read_tests()  # Получаем список всех тестов
    test = next((test for test in tests if test['id'] == test_id), None)  # Ищем нужный тест

    if not test:
        flash("Тест не найден"), 404
        return render_template('index')

    if request.method == 'POST':
        user_answers = request.form.getlist('user_answers')
        correct_answers = test['answers']
        scores = []
        explanations = []
        
        # Имя текущего пользователя и название теста
        username = session['username']
        test_name = test['name']

        for question, user_answer, correct_answer in zip(test['questions'], user_answers, correct_answers):
            question_text = f"Сравни ответ пользователя: '{user_answer}' с правильным ответом: '{correct_answer}' на вопрос: '{question}'. Поставь оценку от 0 до 100. В первой строке укажи только число оценки. Далее, объясни, почему ты поставил эту оценку."
            response = giga_chat.ask_a_question(question_text)
            
            # Извлекаем оценку и объяснение
            score, explanation = response.split('\n', 1)
            scores.append(score)
            explanations.append(explanation)

            # Сохраняем результат для каждого вопроса
            save_test_result(username, test_name, question, user_answer, score, explanation)

        average_score = sum(float(score) for score in scores) / len(scores)
        return render_template('test_result.html', test=test, user_answers=user_answers, scores=scores, average_score=average_score, explanations=explanations)

    return render_template('take_test.html', test=test, tests=tests)  # Передаём test и tests


# Регистрация пользователя
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        admin_password = request.form.get('admin_password', '')

        users = read_users()
        if any(user['username'] == username for user in users):
            flash("Пользователь с таким именем уже существует")
            return render_template('register.html')

        role = 'admin' if admin_password == SECRET_ADMIN_PASSWORD else 'user'
        users.append({'username': username, 'password': password, 'role': role})
        write_users(users)
        return redirect(url_for('login'))

    return render_template('register.html')

# Авторизация пользователя
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = read_users()
        user = next((user for user in users if user['username'] == username and user['password'] == password), None)

        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            flash("Неверное имя пользователя или пароль")
            return render_template('login.html')

    return render_template('login.html')

# Выход из системы
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
