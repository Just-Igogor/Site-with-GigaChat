import csv
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

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

        # Сравнение с использованием GigaChat
        scores = []
        for i in range(len(user_answers)):
            score = compare_answers(user_answers[i], correct_answers[i])  # Предположим, GigaChat возвращает оценку
            scores.append(score)
        
        average_score = sum(scores) / len(scores)
        return render_template('test_result.html', test=test, user_answers=user_answers, scores=scores, average_score=average_score)

    return render_template('take_test.html', test=test)

if __name__ == '__main__':
    app.run(debug=True)

