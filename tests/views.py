from django.shortcuts import render, get_object_or_404, redirect
from .models import Test, Question, Answer, TestResult
from .forms import QuestionForm, TestForm, AnswerForm, AnswerFormSet
from django.core.paginator import Paginator
from django.contrib import messages
from django.forms import modelformset_factory
from django.utils import timezone
import random
from notifications.models import Notification
from decimal import Decimal


def take_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.all()

    # Проверка, с какой страницы был перенаправлен пользователь
    referer_url = request.META.get('HTTP_REFERER', '')
    print(f"Пользователь был перенаправлен с: {referer_url}")

    # Если пользователь пришёл со страницы "start", сбросим сессию и начнём тест с начала
    if 'intro' in referer_url:
        print("Пользователь пришёл со страницы start, сбрасываем сессию.")
        request.session.pop('test_start_time', None)
        request.session.pop('current_question_number', None)
        request.session.pop('user_answers', None)
        request.session.pop('time_left', None)

    # Проверяем, есть ли уже результаты для данного теста
    test_result = TestResult.objects.filter(user=request.user, test=test).first()

    # Логируем содержимое сессии перед началом теста
    print("Содержимое сессии:", request.session.items())

    # Если тест завершен, перенаправляем на результаты
    if test_result and test_result.completed_at:
        messages.info(request, 'Вы уже завершили этот тест.')
        return redirect('test_results', test_id=test.id)

    # Если тест только начался, сохраняем начальное время
    if 'test_start_time' not in request.session:
        request.session['test_start_time'] = timezone.now().isoformat()
        time_left = test.time_limit * 60  # Время на тест в секундах
    else:
        # Получаем стартовое время из сессии и вычисляем, сколько времени осталось
        test_start_time = timezone.datetime.fromisoformat(request.session['test_start_time'])
        time_spent = timezone.now() - test_start_time
        time_left = request.session.get('time_left', test.time_limit * 60) - time_spent.total_seconds()

        # Если время истекло, завершаем тест
        if time_left <= 0:
            messages.error(request, "Время для теста истекло.")
            return redirect('test_results', test_id=test.id)

    # Сохраняем оставшееся время в сессии для дальнейших запросов
    request.session['time_left'] = time_left

    current_question_number = request.session.get('current_question_number', 1)
    current_question = questions[current_question_number - 1]

    # Перемешиваем варианты ответов
    answers = list(current_question.answers.all())
    random.shuffle(answers)
    current_question.answers_shuffled = answers

    if request.method == 'POST':
        user_answers = request.session.get('user_answers', {})

        # Сохранение ответов пользователя
        if current_question.question_type == 'multiple':
            user_answer = request.POST.getlist(f'question_{current_question.id}_answers')
        elif current_question.question_type == 'sequence':
            user_answer = {
                answer.id: request.POST.get(f'question_{current_question.id}_order_{answer.id}')
                for answer in current_question.answers.all()
            }
        elif current_question.question_type == 'match':
            user_answer = {
                answer.id: request.POST.get(f'question_{current_question.id}_match_{answer.id}')
                for answer in current_question.answers.all()
            }
        else:
            user_answer = request.POST.get(f'question_{current_question.id}')

        user_answers[str(current_question.id)] = user_answer
        request.session['user_answers'] = user_answers

        # Переход к следующему вопросу
        if current_question_number < len(questions):
            request.session['current_question_number'] = current_question_number + 1
            return redirect('take_test', test_id=test.id)

        # Оценка теста и сохранение результатов
        score = evaluate_test(test, user_answers, request)
        if score >= test.passing_score:
            messages.success(request, f"Тест пройден. Ваш результат: {score}%")
        else:
            messages.error(request, f"Тест не пройден. Ваш результат: {score}%")

        # Сброс данных сессии
        del request.session['user_answers']
        del request.session['current_question_number']
        del request.session['test_start_time']
        del request.session['time_left']

        return redirect('test_results', test_id=test.id)

    return render(request, 'take_test.html', {
        'test': test,
        'current_question': current_question,
        'current_question_number': current_question_number,
        'is_last_question': current_question_number == len(questions),
        'time_left': int(time_left),
    })


def create_test(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tests_list')
    else:
        form = TestForm()
    return render(request, 'create_test.html', {'form': form})


def add_question(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        formset = AnswerFormSet(request.POST)

        if question_form.is_valid() and formset.is_valid():
            question = question_form.save(commit=False)
            question.test = test
            question.save()

            # Проверяем тип вопроса и добавляем только 2 варианта для типа 'true_false'
            if question.question_type == 'true_false':
                Answer.objects.create(question=question, text="Верно", is_correct=True)
                Answer.objects.create(question=question, text="Неверно", is_correct=False)
            else:
                formset.instance = question
                formset.save()

            return redirect('tests_list')
    else:
        question_form = QuestionForm()
        formset = AnswerFormSet()

    return render(request, 'add_question.html', {'question_form': question_form, 'formset': formset, 'test': test})



def tests_list(request):
    search_query = request.GET.get('search', '')
    tests = Test.objects.all()

    if search_query:
        tests = tests.filter(title__icontains=search_query)

    paginator = Paginator(tests, 50)  # Пагинация по 50 записей
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for test in page_obj:
        test.actual_questions = test.questions.count()  # Количество вопросов в базе
        test.is_complete = test.actual_questions >= test.required_questions  # Проверка на достаточность вопросов

    return render(request, 'tests_list.html', {'page_obj': page_obj, 'search_query': search_query})


def edit_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if request.method == 'POST':
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            return redirect('tests_list')
    else:
        form = TestForm(instance=test)

    return render(request, 'edit_test.html', {'form': form, 'test': test})


def delete_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if request.method == 'POST':
        test.delete()
        return redirect('tests_list')

    return render(request, 'delete_test_confirm.html', {'test': test})


def questions_list(request, test_id):
    search_query = request.GET.get('search', '')
    test = get_object_or_404(Test, id=test_id)
    questions = test.questions.all()

    if search_query:
        questions = questions.filter(text__icontains=search_query)

    paginator = Paginator(questions, 50)  # Пагинация по 50 записей
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'questions_list.html', {'page_obj': page_obj, 'search_query': search_query, 'test': test})


def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        if form.is_valid():
            form.save()
            return redirect('questions_list', test_id=question.test.id)
    else:
        form = QuestionForm(instance=question)

    return render(request, 'edit_question.html', {'form': form, 'question': question})


def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.method == 'POST':
        question.delete()
        return redirect('questions_list', test_id=question.test.id)

    return render(request, 'delete_question_confirm.html', {'question': question})


def evaluate_test(test, user_answers, request):
    total_score = 0.0
    max_score = 0.0
    correct_answers_count = 0

    for question in test.questions.all():
        question_id_str = str(question.id)

        if question.question_type == 'single':
            user_answer = user_answers.get(question_id_str)
            score = evaluate_single(question, user_answer)
            total_score += score
            max_score += 1
            if score == 1.0:
                correct_answers_count += 1

        elif question.question_type == 'multiple':
            user_answer = user_answers.get(question_id_str)
            score = evaluate_multiple(question, user_answer)
            total_score += score
            max_score += 1
            if score == 1.0:
                correct_answers_count += 1

        elif question.question_type == 'true_false':
            user_answer = user_answers.get(question_id_str)
            score = evaluate_true_false(question, user_answer)
            total_score += score
            max_score += 1
            if score == 1.0:
                correct_answers_count += 1

        elif question.question_type == 'sequence':
            user_answer = user_answers  # Обрабатываем ответы для последовательности
            score = evaluate_sequence(question, user_answer)
            total_score += score
            max_score += 1
            if score == 1.0:
                correct_answers_count += 1

        elif question.question_type == 'match':
            user_answer = user_answers  # Обрабатываем ответы для соответствий
            score = evaluate_match(question, user_answer)
            total_score += score
            max_score += 1
            if score == 1.0:
                correct_answers_count += 1

    total_questions_count = test.questions.count()

    if max_score > 0:
        percentage_score = round((total_score / max_score) * 100, 1)
    else:
        percentage_score = 0

    # Сохраняем результат с правильными ответами и общим количеством вопросов
    TestResult.objects.create(
        user=request.user,
        test=test,
        score=percentage_score,
        correct_answers_count=correct_answers_count,
        total_questions_count=total_questions_count
    )

    return percentage_score


def evaluate_single(question, user_answer):
    """Оценка вопроса с одним верным ответом"""
    correct_answer = question.answers.filter(is_correct=True).first()
    print(correct_answer)
    print(user_answer)
    # Проверяем, что пользователь выбрал ответ
    if user_answer is None:
        print(f"Ответ на вопрос {question.id} не выбран")
        return 0.0  # Если ответа нет, возвращаем 0 баллов

    print(f"Правильный ответ: {correct_answer.text}, Ответ пользователя: {user_answer}")

    try:
        if correct_answer and correct_answer.id == int(user_answer):
            return 1.0  # Верный ответ, полный балл
    except (ValueError, TypeError):
        print("Ошибка преобразования ответа в число")
        return 0.0  # Неверный ответ или некорректный формат

    return 0.0  # Неверный ответ


def evaluate_multiple(question, user_answers):
    """Оценка вопроса с несколькими верными ответами"""
    correct_answers = question.answers.filter(is_correct=True).values_list('id', flat=True)

    if not user_answers:
        print(f"Ответы на вопрос {question.id} не выбраны")
        return 0.0  # Если ответов нет, возвращаем 0 баллов

    try:
        selected_answers = [int(ans) for ans in user_answers]
        print(f"Правильные ответы: {correct_answers}, Ответы пользователя: {selected_answers}")
    except (ValueError, TypeError):
        print("Ошибка преобразования ответов в числа")
        return 0.0  # Некорректный формат ответа

    if set(correct_answers) == set(selected_answers):
        return 1.0  # Все правильные ответы выбраны
    elif set(correct_answers).intersection(set(selected_answers)):
        return 0.5  # Часть правильных ответов выбрана
    return 0.0  # Неверные ответы


def evaluate_true_false(question, user_answer):
    """Оценка вопроса типа верно/неверно"""
    correct_answer = question.answers.filter(is_correct=True).first()
    if correct_answer.text == 'Верно':
        correct_answer.text = 'true'
    else:
        correct_answer.text = 'false'


    if user_answer is None:
        print(f"Ответ на вопрос {question.id} не выбран")
        return 0.0  # Если ответ не выбран, возвращаем 0 баллов

    print(f"Правильный ответ: {correct_answer.text}, Ответ пользователя: {user_answer}")

    try:
        if correct_answer.text == user_answer:
            return 1.0  # Верный ответ
    except (ValueError, TypeError):
        print("Ошибка преобразования ответа в число")
        return 0.0  # Некорректный формат ответа

    return 0.0  # Неверный ответ


def evaluate_sequence(question, user_answers):
    """Оценка последовательности"""
    correct_order = list(question.answers.order_by('sequence_order').values_list('id', flat=True))

    if not user_answers:
        return 0.0

    try:
        user_order = [int(user_answers.get(f'question_{question.id}_{answer_id}')) for answer_id in correct_order]
    except (ValueError, TypeError):
        return 0.0

    if correct_order == user_order:
        return 1.0
    return 0.0


def evaluate_match(question, user_answers):
    """Оценка соответствия"""
    correct_matches = {str(answer.id): answer.match_pair for answer in question.answers.all()}

    if not user_answers:
        return 0.0

    try:
        user_matches = {str(answer_id): user_answers.get(f'question_{question.id}_{answer_id}') for answer_id in correct_matches.keys()}
    except (ValueError, TypeError):
        return 0.0

    if correct_matches == user_matches:
        return 1.0
    return 0.0


def test_results(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    user = request.user

    # Проверяем, существует ли результат теста для данного пользователя и теста
    test_result = TestResult.objects.filter(user=user, test=test).first()

    if not test_result:
        # Если результата теста нет, возвращаем сообщение об ошибке или создаем его
        messages.error(request, 'Результат теста не найден. Сначала завершите тест.')
        return redirect('test_intro', test_id=test.id)

    test_score = Decimal(test_result.score)
    passing_score = Decimal(test.passing_score)
    # Далее продолжаем логику работы с результатом теста
    if test_score >= passing_score:
        messages.success(request, 'Поздравляем! Вы прошли тест.')
    else:
        messages.error(request, 'К сожалению, вы не прошли тест.')

    return render(request, 'test_results.html', {'test_result': test_result})


def test_instructions(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    # Проверяем наличие завершенных тестов
    test_result = TestResult.objects.filter(user=request.user, test=test).first()

    # if test_result and test_result.completed_at:
    #     messages.info(request, 'Вы уже завершили этот тест.')
    #     return redirect('test_results', test_id=test.id)

    # Инициализируем сессию для начала теста
    if 'test_start_time' not in request.session:
        request.session['test_start_time'] = timezone.now().isoformat()

    return render(request, 'test_instructions.html', {'test': test})


def notify_user(user, message):
    """Функция для создания уведомления"""
    Notification.objects.create(user=user, message=message)