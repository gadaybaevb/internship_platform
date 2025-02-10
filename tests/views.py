from django.shortcuts import render, get_object_or_404, redirect
from .models import Test, Question, Answer, TestResult, TestQuestionResult
from .forms import QuestionForm, TestForm, AnswerForm, AnswerFormSet
from django.core.paginator import Paginator
from django.contrib import messages
from django.forms import modelformset_factory
from django.utils import timezone
import random
import json
from notifications.models import Notification
from internships.models import Internship
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required


@login_required
def take_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    # Reset session data if the test is restarted
    referer_url = request.META.get('HTTP_REFERER', '')
    if 'intro' in referer_url:
        for key in ['test_start_time', 'current_question_number', 'user_answers', 'question_order']:
            if key in request.session:
                del request.session[key]

    # Check if the user already completed the test
    test_result = TestResult.objects.filter(user=request.user, test=test).first()
    if test_result and test_result.completed_at:
        messages.info(request, 'Вы уже завершили этот тест.')
        return redirect('test_results', test_id=test.id)

    # Initialize start time and question order if not set in session
    if 'test_start_time' not in request.session:
        request.session['test_start_time'] = timezone.now().isoformat()

        # Create and save a randomized order of question IDs
        question_ids = list(test.questions.values_list('id', flat=True))
        # Select required number of questions randomly
        if len(question_ids) > test.required_questions:
            question_ids = random.sample(question_ids, test.required_questions)
        random.shuffle(question_ids)
        request.session['question_order'] = question_ids

    # Calculate time left based on fixed start time
    test_start_time = timezone.datetime.fromisoformat(request.session['test_start_time'])
    time_spent = timezone.now() - test_start_time
    time_left = test.time_limit * 60 - time_spent.total_seconds()

    # Check if time is up
    if time_left <= 0:
        return finish_test_and_redirect(request, test, "Время для теста истекло.")

    # Load questions in randomized order
    question_order = request.session['question_order']
    current_question_number = request.session.get('current_question_number', 1)
    current_question_id = question_order[current_question_number - 1]
    current_question = get_object_or_404(Question, id=current_question_id)

    # Calculate the number of answered questions
    answered_questions_count = current_question_number - 1

    # Shuffle and prepare answers for display
    answers = list(current_question.answers.all())
    random.shuffle(answers)
    current_question.answers_shuffled = answers

    # Prepare initial pairs for match questions
    if current_question.question_type == 'match':
        initial_pairs = {
            "left": [(str(answer.id), answer.text) for answer in answers],
            "right": [(str(answer.id), answer.match_pair) for answer in answers if answer.match_pair]
        }
        random.shuffle(initial_pairs["left"])
        random.shuffle(initial_pairs["right"])
        current_question.initial_pairs = initial_pairs
    else:
        initial_pairs = None

    # Handle POST request for submitting answers
    if request.method == 'POST':
        user_answers = request.session.get('user_answers', {})

        # Collect answer based on question type
        if current_question.question_type == 'multiple':
            user_answer = request.POST.getlist(f'question_{current_question.id}_answers')
        elif current_question.question_type == 'sequence':
            user_answer = request.POST.get(f'question_{current_question.id}_sequence')
        elif current_question.question_type == 'match':
            user_answer = request.POST.get(f"question_{current_question.id}_matches")
            try:
                user_answer = json.loads(user_answer) if user_answer else initial_pairs
            except json.JSONDecodeError:
                user_answer = {}
            user_answers[f"{current_question.id}_matches"] = json.dumps(user_answer)
        else:
            user_answer = request.POST.get(f'question_{current_question.id}')

        # Save user answer to session
        user_answers[str(current_question.id)] = user_answer
        request.session['user_answers'] = user_answers

        # Move to the next question or finish the test
        if current_question_number < len(question_order):
            request.session['current_question_number'] = current_question_number + 1
            return redirect('take_test', test_id=test.id)
        else:
            # Finish the test
            return finish_test_and_redirect(request, test, "Тест завершен.")

    return render(request, 'take_test.html', {
        'test': test,
        'current_question': current_question,
        'current_question_number': current_question_number,
        'answered_questions_count': answered_questions_count,
        'is_last_question': current_question_number == len(question_order),
        'time_left': int(time_left),  # Use fixed `time_left` for consistent countdown
        'initial_pairs': initial_pairs
    })


def finish_test_and_redirect(request, test, message):
    """Helper function to finalize the test and redirect to the results page."""
    user_answers = request.session.get('user_answers', {})
    score = evaluate_test(test, user_answers, request)
    result_message = f"{message} Ваш результат: {score}%."
    messages.success(request, result_message)

    # Clean up session data after test completion
    for key in ['user_answers', 'current_question_number', 'test_start_time', 'time_left']:
        if key in request.session:
            del request.session[key]

    return redirect('test_results', test_id=test.id)


@login_required
def create_test(request):
    if request.method == 'POST':
        form = TestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tests_list')
    else:
        form = TestForm()
    return render(request, 'create_test.html', {'form': form})


@login_required
def add_question(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    AnswerFormSet = modelformset_factory(Answer, form=AnswerForm, extra=4, can_delete=True)

    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        formset = AnswerFormSet(request.POST, queryset=Answer.objects.none())

        if question_form.is_valid() and formset.is_valid():
            question = question_form.save(commit=False)
            question.test = test

            # Получаем данные о типе вопроса и ответах
            question_type = question.question_type
            answers = [form.cleaned_data for form in formset if form.cleaned_data.get('text')]

            # Валидация ответов на основе типа вопроса
            if question_type == 'single':
                correct_answers = [answer for answer in answers if answer.get('is_correct')]
                if len(correct_answers) != 1:
                    messages.error(request, 'Для типа "single" должен быть выбран ровно один правильный ответ.')
                    return render(request, 'add_question.html',
                                  {'question_form': question_form, 'formset': formset, 'test': test})

            elif question_type == 'multi':
                correct_answers = [answer for answer in answers if answer.get('is_correct')]
                if len(correct_answers) <= 1 or len(correct_answers) == len(answers):
                    messages.error(request, 'Для типа "multi" выберите больше одного, но не все ответы как правильные.')
                    return render(request, 'add_question.html',
                                  {'question_form': question_form, 'formset': formset, 'test': test})

            elif question_type == 'true_false':
                if len(answers) != 2 or sum(1 for answer in answers if answer.get('is_correct')) != 1:
                    messages.error(request,
                                   'Для типа "true_false" должно быть ровно два ответа, и один из них должен быть правильным.')
                    return render(request, 'add_question.html',
                                  {'question_form': question_form, 'formset': formset, 'test': test})

            # elif question_type == 'match':
            #     if not all(answer.get('text') and answer.get('match_pair') for answer in answers):
            #         messages.error(request, 'Для типа "match" каждая пара вопрос-ответ должна быть заполнена.')
            #         return render(request, 'add_question.html',
            #                       {'question_form': question_form, 'formset': formset, 'test': test})

            # Если все проверки пройдены, сохраняем вопрос и ответы
            question.save()

            # Для 'true_false' добавляем только два варианта ответа
            if question_type == 'true_false':
                Answer.objects.create(question=question, text="Верно", is_correct=True)
                Answer.objects.create(question=question, text="Неверно", is_correct=False)
            else:
                # Сохраняем ответы для других типов вопросов
                for form in formset:
                    if form.cleaned_data.get('text'):  # Проверка, что текст ответа не пустой
                        answer = form.save(commit=False)
                        answer.question = question
                        answer.save()

            return redirect('tests_list')
    else:
        question_form = QuestionForm()
        formset = AnswerFormSet(queryset=Answer.objects.none())

    return render(request, 'add_question.html', {'question_form': question_form, 'formset': formset, 'test': test})


@login_required
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


@login_required
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


@staff_member_required
def delete_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if request.method == 'POST':
        test.delete()
        return redirect('tests_list')

    return render(request, 'delete_test_confirm.html', {'test': test})


@login_required
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


@login_required
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    AnswerFormSet = modelformset_factory(Answer, form=AnswerForm, extra=1, can_delete=True)

    if request.method == 'POST':
        form = QuestionForm(request.POST, instance=question)
        formset = AnswerFormSet(request.POST, queryset=question.answers.all())

        if form.is_valid() and formset.is_valid():
            answers = [f.cleaned_data for f in formset if f.cleaned_data and not f.cleaned_data.get('DELETE', False)]
            question_type = form.cleaned_data['question_type']
            valid = True

            # Валидация ответов в зависимости от типа вопроса
            if question_type == 'single':
                correct_answers = [a for a in answers if a.get('is_correct')]
                if len(correct_answers) != 1:
                    messages.error(request, 'Для типа "single" должен быть выбран ровно один правильный ответ.')
                    valid = False

            elif question_type == 'multi':
                correct_answers = [a for a in answers if a.get('is_correct')]
                if len(correct_answers) <= 1:
                    messages.error(request, 'Для типа "multi" выберите больше одного правильного ответа.')
                    valid = False

            elif question_type == 'true_false':
                if len(answers) != 2 or sum(1 for a in answers if a.get('is_correct')) != 1:
                    messages.error(request, 'Для типа "true_false" должно быть ровно два ответа, и один из них должен быть правильным.')
                    valid = False

            if valid:
                form.save()
                formset.save()  # Сохранение всех изменений в formset
                messages.success(request, "Вопрос и ответы успешно сохранены.")
                return redirect('questions_list', test_id=question.test.id)
        else:
            if not form.is_valid():
                print("Ошибки формы вопроса:", form.errors)
            if not formset.is_valid():
                print("Ошибки formset ответов:", formset.errors)

    else:
        form = QuestionForm(instance=question)
        formset = AnswerFormSet(queryset=question.answers.all())

    return render(request, 'edit_question.html', {
        'form': form,
        'formset': formset,
        'question': question
    })


@staff_member_required
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

    # Создаем экземпляр TestResult
    test_result = TestResult.objects.create(
        user=request.user,
        test=test,
        score=0,  # Оценка будет обновлена позже
        correct_answers_count=0,
        total_questions_count=len(request.session.get('question_order', []))  # Учитываем только заданные вопросы
    )

    # Проходим только по заданным вопросам
    for question_id in request.session.get('question_order', []):
        question = test.questions.get(id=question_id)
        question_id_str = str(question.id)
        options = {str(answer.id): answer.text for answer in question.answers.all()}
        user_answer_keys = user_answers.get(question_id_str) or user_answers.get(f"{question_id_str}_matches")
        user_answer_values = [options.get(str(key), "Неизвестный ответ") for key in user_answer_keys] if user_answer_keys else []
        is_correct = False
        correct_answer = {}

        # Преобразуем keys в список, если он строка
        if isinstance(user_answer_keys, str):
            user_answer_keys = [user_answer_keys]

            # Если values пустые или содержат только "Неизвестный ответ", заменяем на keys
        if not user_answer_values or all(v == "Неизвестный ответ" for v in user_answer_values):
            user_answer_values = [options.get(k, "Неизвестный ответ") for k in user_answer_keys]

        # Обработка разных типов вопросов
        if question.question_type == 'single':
            score = evaluate_single(question, user_answer_values[0])
            correct_answer = {str(answer.id): answer.text for answer in question.answers.filter(is_correct=True)}
            is_correct = score == 1.0

        elif question.question_type == 'multiple':
            score = evaluate_multiple(question, user_answer_keys)
            correct_answer = {str(answer.id): answer.text for answer in question.answers.filter(is_correct=True)}
            is_correct = score == 1.0

        elif question.question_type == 'true_false':
            score = evaluate_true_false(question, user_answer_keys)
            correct_answer = {str(answer.id): answer.text for answer in question.answers.filter(is_correct=True)}
            is_correct = score == 1.0

        elif question.question_type == 'sequence':
            score = evaluate_sequence(question, user_answer_keys)
            correct_answer = {str(answer.id): answer.text for answer in question.answers.order_by('sequence_order')}
            is_correct = score == 1.0

        elif question.question_type == 'match':
            score = evaluate_match(question, user_answer_keys)
            correct_answer = {str(answer.id): answer.match_pair for answer in question.answers.all()}
            is_correct = score == 1.0

        # Сохраняем результаты вопроса
        TestQuestionResult.objects.create(
            test_result=test_result,
            question_text=question.text,
            question_type=question.question_type,
            options=options,
            user_answer={"keys": user_answer_keys, "values": user_answer_values},  # Сохраняем ключи и текстовые значения
            correct_answer=correct_answer,  # Запись правильного ответа
            is_correct=is_correct
        )

        # Обновляем общие показатели
        total_score += score
        max_score += 1
        if is_correct:
            correct_answers_count += 1

    # Обновляем итоговый результат теста
    test_result.score = round((total_score / max_score) * 100, 1) if max_score > 0 else 0
    test_result.correct_answers_count = correct_answers_count
    test_result.save()

    return test_result.score


def evaluate_single(question, user_answer):
    """Оценка вопроса с одним верным ответом"""
    correct_answer = question.answers.filter(is_correct=True).first()
    # Проверяем, что пользователь выбрал ответ
    if user_answer is None:
        return 0.0  # Если ответа нет, возвращаем 0 баллов
    print(user_answer, type(user_answer))
    print(correct_answer, type(user_answer))
    try:
        if str(correct_answer) == str(user_answer):
            return 1.0  # Верный ответ, полный балл
    except (ValueError, TypeError):
        print("Ошибка преобразования ответа в число")
        return 0.0  # Неверный ответ или некорректный формат

    return 0.0  # Неверный ответ


def evaluate_multiple(question, user_answers):
    """Оценка вопроса с несколькими верными ответами"""
    correct_answers = question.answers.filter(is_correct=True).values_list('id', flat=True)

    if not user_answers:
        return 0.0  # Если ответов нет, возвращаем 0 баллов

    try:
        selected_answers = [int(ans) for ans in user_answers]
    except (ValueError, TypeError):
        print("Ошибка преобразования ответов в числа")
        return 0.0  # Некорректный формат ответа
    print('selected_answers: ', selected_answers)
    print('correct_answers: ', correct_answers)
    if set(selected_answers) == set(correct_answers):
        print('1 score')
        return 1.0  # Все правильные ответы выбраны

    elif set(selected_answers) & set(correct_answers):  # Есть хотя бы один правильный ответ
        print('0,5 score')
        return 0.5
    print('0 score')
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


    try:
        if correct_answer.text == user_answer:
            return 1.0  # Верный ответ
    except (ValueError, TypeError):
        print("Ошибка преобразования ответа в число")
        return 0.0  # Некорректный формат ответа

    return 0.0  # Неверный ответ


def evaluate_sequence(question, user_answer):
    """Оценка вопроса типа последовательность (перетаскивание карточек)"""
    # Получаем правильный порядок ответов
    correct_order = list(question.answers.order_by('id').values_list('id', flat=True))
    if not user_answer:
        print("Ответ пользователя отсутствует.")
        return 0.0

    # Преобразуем ответ пользователя из JSON-строки в список
    try:
        user_order_ = json.loads(user_answer)  # Преобразуем JSON в список id
        user_order = [int(i) for i in user_order_]
    except (ValueError, TypeError):
        print("Ошибка при обработке ответа.")
        return 0.0

    # Сравниваем правильную последовательность с пользовательской
    if correct_order == user_order:
        return 1.0
    return 0.0


def evaluate_match(question, user_answer):
    """Оценка вопроса типа соответствие"""

    # Получаем правильные соответствия как множество кортежей (id ответа, match_pair)
    correct_matches = {(str(answer.id), str(answer.match_pair)) for answer in question.answers.all()}

    if not user_answer:
        print("Ответ пользователя для match пуст или None")
        return 0.0

    try:
        # Преобразуем ответ пользователя в словарь и создаем множество кортежей
        user_matches_dict = json.loads(user_answer) if isinstance(user_answer, str) else user_answer
        # Убедимся, что все значения в user_matches_dict приведены к строкам для надежного сравнения
        user_matches = {(str(key), str(value)) for key, value in user_matches_dict.items()}

    except (json.JSONDecodeError, TypeError):
        print("Ошибка при декодировании JSON ответа пользователя для match")
        return 0.0

    # Сравниваем правильные пары и пары пользователя
    if correct_matches == user_matches:
        print("Ответ пользователя для match полностью правильный.")
        return 1.0  # Полный балл за правильный ответ
    else:
        print(f"Несоответствие: правильные пары - {correct_matches}, пары пользователя - {user_matches}")
        return 0.0  # Неверный ответ


@login_required
def test_results(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    user = request.user

    # Проверяем, существует ли результат теста для данного пользователя и теста
    test_result = TestResult.objects.filter(user=user, test=test).first()

    if not test_result:
        # Если результата теста нет, возвращаем сообщение об ошибке или создаем его
        messages.error(request, 'Результат теста не найден. Сначала завершите тест.')
        return redirect('test_intro', test_id=test.id)

    # Количество вопросов из session (заданные вопросы)
    question_order = request.session.get('question_order', [])
    total_questions_count = len(question_order) if question_order else test_result.total_questions_count

    test_score = Decimal(test_result.score).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)  # Округляем до двух знаков
    passing_score = Decimal(test.passing_score).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)  # Округляем до двух знаков

    # Далее продолжаем логику работы с результатом теста
    if test_score >= round(passing_score, 0):
        messages.success(request, 'Поздравляем! Вы прошли тест.')
    else:
        messages.error(request, 'К сожалению, вы не прошли тест.')

    message = f"Стажер {user.username} ({user.full_name}) сдал экзамен {test_result.test}, на {test_score}."
    Notification.objects.create(user=user, message=message)

    # Отправка уведомления ментору
    internship = Internship.objects.filter(intern=user).first()
    if internship and internship.mentor:
        Notification.objects.create(user=internship.mentor, message=message)

    return render(request, 'test_results.html', {
        'test_result': test_result,
        'test_score': test_score,
        'passing_score': passing_score,
        'total_questions_count': total_questions_count  # Передаем правильное количество вопросов
    })


@login_required
def test_instructions(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    # Проверяем, является ли пользователь суперпользователем или администратором
    if request.user.is_superuser or request.user.role == 'admin':
        # Суперпользователь и администратор всегда имеют доступ к тесту
        test_result_exists = False
    else:
        # Проверка наличия завершенных тестов по стажеру
        intern_id = request.user.id
        test_result_exists = TestResult.objects.filter(user__id=intern_id, test=test).exists()

    # Если тест уже пройден, перенаправляем к результатам
    if test_result_exists:
        messages.info(request, 'Вы уже завершили этот тест.')
        return redirect('test_results', test_id=test.id)

    # Инициализация сессии для начала теста
    if 'test_start_time' not in request.session:
        request.session['test_start_time'] = timezone.now().isoformat()

    return render(request, 'test_instructions.html', {'test': test})


@login_required
def notify_user(user, message):
    """Функция для создания уведомления"""
    Notification.objects.create(user=user, message=message)


def test_report(request, test_result_id):
    # Получаем результат теста
    test_result = get_object_or_404(TestResult, id=test_result_id)

    # Получаем детализированные результаты каждого вопроса для данного теста
    question_results = TestQuestionResult.objects.filter(test_result=test_result)

    # Формируем данные для шаблона
    questions_with_answers = []
    for question_result in question_results:
        # Получаем правильные ответы
        correct_answers = list(question_result.correct_answer.values()) if question_result.correct_answer else []

        # Получаем пользовательские ответы
        user_answer_data = question_result.user_answer or {}  # Гарантируем, что это словарь
        # Проверяем, если "keys" строка, преобразуем её в список
        user_answer_keys = user_answer_data.get("keys", [])
        if isinstance(user_answer_keys, str):
            user_answer_keys = [user_answer_keys]  # Преобразуем строку в список
        elif not isinstance(user_answer_keys, list):
            user_answer_keys = []  # Если "keys" не строка и не список (например, None), то превращаем в пустой список

        # Фильтруем "values", убирая "Неизвестный ответ"
        user_answers = [
            answer for answer in user_answer_data.get("values", []) if answer != "Неизвестный ответ"
        ]
        print("ываыва,", user_answer_data.get("values", []))
        # Если ответ правильный, заменить пользовательские ответы на правильные
        if question_result.is_correct:
            user_answers = correct_answers

        # Подготавливаем варианты ответа с указанием правильности
        answers = []

        # Если user_answer_keys равно None, заменяем его на пустой список
        for answer_id, answer_text in question_result.options.items():
            answers.append({
                'id': answer_id,
                'text': answer_text,
                'is_user_selected': str(answer_id) in user_answer_keys,  # Теперь user_answer_keys точно список
                'is_correct': str(answer_id) in (question_result.correct_answer or {}).keys()
            })

        # Определяем, правильный ли ответ пользователя
        correct_answer_keys = list((question_result.correct_answer or {}).keys())  # Преобразуем в список
        user_answer_keys_set = set(user_answer_keys)  # Преобразуем в множество
        correct_answer_keys_set = set(correct_answer_keys)  # Преобразуем в множество

        # Сравниваем множества
        print('correct_answer_keys ', correct_answer_keys)
        print('user_answer_keys_set ', user_answer_keys_set)
        print('correct_answer_keys_set ', correct_answer_keys_set)

        is_user_correct = user_answer_keys_set == correct_answer_keys_set
        print(is_user_correct)

        # Добавляем данные вопроса
        questions_with_answers.append({
            'question_text': question_result.question_text,
            'answers': answers,
            'user_answers': user_answers,  # Обновленные ответы пользователя
            'correct_answers': correct_answers,
            'is_user_correct': is_user_correct
        })

    # Отправляем данные в шаблон
    return render(request, 'test_report.html', {
        'test_result': test_result,
        'questions_with_answers': questions_with_answers,
        'test_date': test_result.completed_at.strftime('%d.%m.%Y %H:%M')
    })











