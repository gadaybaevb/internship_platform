from django.shortcuts import render, get_object_or_404, redirect
from .models import Material, Position, Internship, StageProgress, MaterialProgress
from departments.models import Department
from django.contrib.auth import get_user_model
from .forms import MaterialForm, ReviewForm, AddInternForm
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.contrib import messages
from users.models import CustomUser
from .utils import create_stage_progress
from datetime import timedelta, datetime
from django.utils import timezone
from notifications.models import Notification
from tests.models import Test, TestResult
from django.utils.dateparse import parse_date
from django.db.models import Avg, F
from django.contrib.messages import get_messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required


User = get_user_model()


@login_required
def material_list(request):
    search_query = request.GET.get('search', '')
    department_filter = request.GET.get('department', '')
    position_filter = request.GET.get('position', '')
    stage_filter = request.GET.get('stage', '')

    # Получаем все материалы
    materials = Material.objects.all()

    # Фильтрация по поисковому запросу
    if search_query:
        materials = materials.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(position__name__icontains=search_query)
        )

    # Фильтрация по департаменту
    if department_filter:
        materials = materials.filter(position__department__id=department_filter)

    # Фильтрация по позиции
    if position_filter:
        materials = materials.filter(position__id=position_filter)

    # Фильтрация по этапу
    if stage_filter:
        materials = materials.filter(stage=stage_filter)

    # Пагинация по 50 записей
    paginator = Paginator(materials, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Получаем списки департаментов и позиций для фильтрации
    departments = Department.objects.all()
    positions = Position.objects.all()

    # Подсчёт общего количества материалов
    total_materials = materials.count()

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'departments': departments,
        'positions': positions,
        'department_filter': department_filter,
        'position_filter': position_filter,
        'stage_filter': stage_filter,
        'total_materials': total_materials,  # Количество материалов
    }
    return render(request, 'material_list.html', context)


@login_required
def material_create(request):
    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES)
        if form.is_valid():
            # Проверка на наличие дубля
            title = form.cleaned_data['title']
            position = form.cleaned_data['position']
            stage = form.cleaned_data['stage']

            if Material.objects.filter(title=title, position=position, stage=stage).exists():
                # Если такой материал уже существует, выводим сообщение об ошибке
                messages.error(request, 'Материал с таким названием, позицией и этапом уже существует.')
            else:
                # Если дубля нет, сохраняем материал
                form.save()
                messages.success(request, 'Материал успешно добавлен.')
                return redirect('material_list')
    else:
        form = MaterialForm()

    # Получаем только сообщения, которые относятся к этому представлению
    storage = get_messages(request)
    relevant_messages = []
    for message in storage:
        if message.level == messages.ERROR or message.level == messages.SUCCESS:
            relevant_messages.append(message)

    return render(request, 'material_form.html', {'form': form})


@login_required
def material_edit(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == 'POST':
        form = MaterialForm(request.POST, request.FILES, instance=material)
        if form.is_valid():
            form.save()
            return redirect('material_list')
    else:
        form = MaterialForm(instance=material)

    return render(request, 'material_form.html', {'form': form, 'material': material})


@login_required
def material_delete(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == 'POST':
        material.delete()
        return redirect('material_list')

    return render(request, 'material_confirm_delete.html', {'material': material})


@staff_member_required
def assign_mentor(request, internship_id):
    internship = get_object_or_404(Internship, id=internship_id)

    if request.method == 'POST':
        mentor_id = request.POST.get('mentor')
        position_id = request.POST.get('position')

        mentor = CustomUser.objects.get(id=mentor_id)
        position = Position.objects.get(id=position_id)

        internship.mentor = mentor
        internship.position = position  # Присваиваем позицию стажировке
        internship.save()

        # Обновляем позицию стажёра в модели CustomUser
        internship.intern.position = position
        internship.intern.save()

        # Создаем этапы стажировки для стажёра, если их ещё нет
        if not StageProgress.objects.filter(intern=internship.intern, position=position).exists():
            create_stage_progress(internship)  # Создаём этапы для стажировки

        messages.success(request, f"Ментор {mentor.username} назначен для стажера {internship.intern.username}, позиция {position.name}.")

        message = f"Ментор {mentor.username} назначен для стажера {internship.intern.username}, позиция {position.name}."
        Notification.objects.create(user=internship.intern, message=message)

        return redirect('internship_list')

    mentors = CustomUser.objects.filter(role='mentor')
    positions = Position.objects.all()  # Получаем все доступные позиции

    context = {
        'internship': internship,
        'mentors': mentors,
        'positions': positions,  # Передаем позиции в шаблон
    }
    return render(request, 'assign_mentor.html', context)


@staff_member_required
def add_intern(request):
    if request.method == 'POST':
        form = AddInternForm(request.POST)
        if form.is_valid():
            # Получаем объекты сразу из формы
            intern = form.cleaned_data['intern']
            mentor = form.cleaned_data['mentor']
            position = form.cleaned_data['position']

            # Создаем новую стажировку
            internship = Internship.objects.create(
                intern=intern,
                mentor=mentor,
                position=position
            )

            messages.success(request, f"Стажировка для {intern.full_name} успешно создана с ментором {mentor.full_name}.")
            return redirect('internship_list')
    else:
        form = AddInternForm()

    return render(request, 'add_intern.html', {'form': form})


@login_required
def internship_list(request):
    search_query = request.GET.get('search', '')  # Получаем запрос поиска
    internships = Internship.objects.all()

    # Если есть запрос на поиск, фильтруем по имени стажера
    if search_query:
        internships = internships.filter(Q(intern__username__icontains=search_query))

    # Пагинация на 50 записей
    paginator = Paginator(internships, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'internship_list.html', {'page_obj': page_obj, 'search_query': search_query})


@login_required
def dashboard(request):
    user = request.user
    check_deadlines(user)  # Проверяем дедлайны

    form = None  # Инициализация переменной `form`

    if user.role == 'admin':
        # Администратор видит всех стажеров и их прогресс
        internships = Internship.objects.select_related('intern', 'mentor', 'position').all()
    elif user.role == 'mentor':
        # Ментор видит только своих стажеров
        internships = Internship.objects.select_related('intern', 'position').filter(mentor=user)

        for internship in internships:
            # Для каждого стажера добавляем количество материалов, ожидающих подтверждения
            pending_materials_count = MaterialProgress.objects.filter(
                intern=internship.intern,
                status='pending'
            ).count()
            internship.pending_materials_count = pending_materials_count

            # Проверяем, оставил ли ментор отзыв
            internship.mentor_review_exists = bool(internship.mentor_feedback)
            internship.is_internship_completed = internship.is_completed()  # Проверка завершения стажировки

        # Обработка формы отзыва
        if request.method == 'POST' and 'internship_id' in request.POST:
            internship_id = request.POST.get('internship_id')
            internship = get_object_or_404(Internship, id=internship_id)
            form = ReviewForm(request.POST, instance=internship)
            if form.is_valid():
                form.save()
                messages.success(request, 'Ваш отзыв был добавлен.')
                return redirect('dashboard')

        form = ReviewForm()  # Пустая форма для добавления отзыва

    else:
        # Стажер видит только свой прогресс
        stage_progress = StageProgress.objects.filter(intern=user).order_by('stage')

        # Проверяем наличие стажировки у стажера
        internship = Internship.objects.filter(intern=user).first()
        if not internship:
            messages.error(request, "У вас нет активной стажировки. Пожалуйста, свяжитесь с администратором.")
            return render(request, 'intern_dashboard.html', {'stage_progress': stage_progress})

        return render(request, 'intern_dashboard.html', {'stage_progress': stage_progress})

    # Добавляем пагинацию по 10 записей на странице
    paginator = Paginator(internships, 10)  # 10 записей на странице
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Для администратора и ментора отображаем стажеров и их прогресс с пагинацией
    return render(request, 'mentor_admin_dashboard.html', {
        'page_obj': page_obj,
        'role': user.role,
        'form': form,  # Передаем форму для отзыва
    })



@login_required
def update_stage_progress(request, stage_id):
    stage = get_object_or_404(StageProgress, id=stage_id)

    # Только ментор может обновить этап
    if request.user.role == 'mentor':
        stage.completed = True
        stage.completion_date = timezone.now()  # Добавляем дату завершения
        stage.save()
        # Сообщение для уведомления
        messages.success(request, f"Этап {stage.stage} для {stage.intern.full_name} отмечен как завершённый.")

        # Уведомляем администратора
        admin_message = f"Стажер {stage.intern.full_name} завершил этап {stage.stage}."
        for admin in CustomUser.objects.filter(role='admin'):
            Notification.objects.create(user=admin, message=admin_message)

    return redirect('dashboard')


@login_required
def intern_materials(request):
    intern = request.user
    internship = Internship.objects.filter(intern=intern).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=internship)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваш отзыв был отправлен.')
            return redirect('intern_materials')

    form = ReviewForm(instance=internship)

    if not internship:
        return render(request, 'intern_materials.html', {'materials': [], 'progress_summary': {}})

    # Рассчитываем дату завершения стажировки
    start_date = internship.start_date
    end_date = start_date + timedelta(days=intern.position.duration_days)

    # Преобразуем end_date в datetime для корректного вычитания
    end_date_time = datetime.combine(end_date, datetime.min.time())
    end_date_time_aware = timezone.make_aware(end_date_time)

    # Рассчитываем оставшееся время в днях
    time_left = (end_date_time_aware - timezone.now()).days if end_date_time_aware > timezone.now() else 0

    # Прогресс по материалам
    materials = Material.objects.filter(position=intern.position).order_by('stage')

    material_list = []
    for material in materials:
        # Проверяем прогресс по материалам для каждого стажера
        material_progress = MaterialProgress.objects.filter(intern=intern, material=material).first()

        if material_progress:
            status = material_progress.status  # Статус материала
        else:
            status = 'not_started'

        material_list.append({
            'material': material,
            'status': status
        })

    total_materials = len(materials)
    completed_materials = MaterialProgress.objects.filter(intern=intern, completed=True).count()
    remaining_materials = total_materials - completed_materials

    progress_summary = {
        'total': total_materials,
        'completed': completed_materials,
        'remaining': remaining_materials,
        'time_left': time_left,
    }

    # Тесты и результаты
    tests = Test.objects.filter(position=intern.position)
    test_results = []  # Список для тестов и результатов
    for test in tests:
        result = TestResult.objects.filter(user=intern, test=test).first()
        if result:
            test_results.append({
                'test': test,
                'result': result,
                'is_completed': True
            })
        else:
            test_results.append({
                'test': test,
                'result': None,
                'is_completed': False
            })

    return render(request, 'intern_materials.html', {
        'materials': material_list,
        'progress_summary': progress_summary,
        'tests': test_results,
        'stage_completion': check_stage_completion,
        'form': form,  # Передаем форму для отзыва
        'internship': internship,  # Передаем саму стажировку
    })


def check_deadlines(user):
    # Получаем все активные этапы стажировки для стажера
    stages_in_progress = StageProgress.objects.filter(intern=user, completed=False)

    for stage in stages_in_progress:
        # Проверяем наличие активной стажировки у стажера
        internship = Internship.objects.filter(intern=stage.intern).first()

        if internship:
            end_date = internship.start_date + timedelta(days=stage.position.duration_days)
            days_left = (end_date - timezone.now().date()).days

            # Если осталось 7 дней до конца этапа или стажировки
            if days_left <= 7 and not stage.intern.notifications.filter(message__contains="7 дней").exists():
                message = f"До завершения этапа {stage.stage} осталось {days_left} дней."
                Notification.objects.create(user=stage.intern, message=message)

            # Если этап уже просрочен
            if days_left <= 0 and not stage.intern.notifications.filter(message__contains="просрочен").exists():
                message = f"Этап {stage.stage} просрочен."
                Notification.objects.create(user=stage.intern, message=message)
        else:
            # Если стажировка не найдена, можно выводить сообщение
            message = "Стажировка не найдена. Пожалуйста, свяжитесь с администратором."
            Notification.objects.create(user=stage.intern, message=message)


@login_required
def mark_material_completed(request, material_id):
    material = get_object_or_404(Material, id=material_id)
    intern = request.user

    # Получаем или создаем прогресс для материала
    material_progress, created = MaterialProgress.objects.get_or_create(
        intern=intern,
        material=material,
        defaults={'status': 'not_started'}
    )

    if request.method == 'POST':
        # Меняем статус на "Ожидание"
        material_progress.status = 'pending'
        material_progress.completed = False  # Сначала ждем подтверждения
        material_progress.save()

        # Отправляем уведомление ментору
        mentor = Internship.objects.filter(intern=intern).first().mentor
        if mentor:
            Notification.objects.create(
                user=mentor,
                message=f"Стажер {intern.full_name} отметил материал '{material.title}' как завершённый. Требуется подтверждение."
            )

        messages.success(request, 'Материал был отмечен как завершённый, ожидается подтверждение ментора.')

    return redirect('intern_materials')


@login_required
def check_stage_completion(intern, stage):
    """Проверка, завершены ли все материалы на этапе"""
    materials_on_stage = Material.objects.filter(position=intern.position, stage=stage)
    completed_materials = MaterialProgress.objects.filter(intern=intern, material__in=materials_on_stage, completed=True).count()

    if completed_materials == materials_on_stage.count():
        # Завершаем этап, если все материалы завершены
        stage_progress, created = StageProgress.objects.get_or_create(intern=intern, stage=stage, position=intern.position)
        stage_progress.completed = True
        stage_progress.completion_date = timezone.now()
        stage_progress.save()

        # Создаем уведомление для стажёра и администратора
        message = f"Этап {stage} завершён."
        Notification.objects.create(user=intern, message=message)

        for admin in CustomUser.objects.filter(role='admin'):
            admin_message = f"Стажёр {intern.full_name} завершил этап {stage}."
            Notification.objects.create(user=admin, message=admin_message)


@login_required
def mentor_view_intern_materials(request, intern_id):
    intern = get_object_or_404(CustomUser, id=intern_id)

    materials = Material.objects.filter(position=intern.position).order_by('stage')
    material_list = []

    for material in materials:
        material_progress = MaterialProgress.objects.filter(intern=intern, material=material).first()

        if material_progress:
            if material_progress.completed:
                status = 'Завершён'
            else:
                status = 'Ожидание'
        else:
            status = 'Не завершён'

        material_list.append({
            'material': material,
            'status': status,
            'progress_id': material_progress.id if material_progress else None
        })

    return render(request, 'mentor_view_intern_materials.html', {
        'intern': intern,
        'materials': material_list
    })


@login_required
def confirm_material_completion(request, progress_id):
    # Получаем запись о прогрессе по материалу
    material_progress = get_object_or_404(MaterialProgress, id=progress_id)

    # Ментор может подтвердить материал
    if request.method == 'POST':
        material_progress.status = 'completed'  # Обновляем статус на завершённый
        material_progress.completed = True
        material_progress.completion_date = timezone.now()
        material_progress.save()

        messages.success(request, 'Материал успешно подтверждён как завершённый.')
        return redirect('dashboard')  # Перенаправляем ментора на его дашборд

    return redirect('mentor_view_intern_materials', intern_id=material_progress.intern.id)


@login_required
def intern_report(request, intern_id):
    intern = get_object_or_404(CustomUser, id=intern_id)
    internship = get_object_or_404(Internship, intern=intern)

    # Получаем все тесты, которые прошел стажер
    test_results = TestResult.objects.filter(user=intern)

    # Дата добавления в систему (это поле должно быть в CustomUser)
    date_added = intern.date_joined

    # Дата завершения стажировки (дата последнего теста)
    if test_results.exists():
        completion_date = test_results.order_by('-completed_at').first().completed_at
    else:
        completion_date = None

    # Ментор стажера
    mentor = internship.mentor

    # Получаем отзывы (если они были оставлены)
    intern_feedback = internship.intern_feedback
    mentor_feedback = internship.mentor_feedback

    return render(request, 'intern_report.html', {
        'intern': intern,
        'internship': internship,
        'test_results': test_results,
        'date_added': date_added,  # Дата создания пользователя
        'completion_date': completion_date,
        'mentor': mentor,
        'intern_feedback': intern_feedback,  # Добавляем отзыв стажера
        'mentor_feedback': mentor_feedback,  # Добавляем отзыв ментора
    })


@staff_member_required
def reports_view(request):
    return render(request, 'reports.html')


@staff_member_required
def test_reports_view(request):
    # Получаем параметры фильтрации
    search_query = request.GET.get('search', '')
    test_query = request.GET.get('test', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Основной запрос для фильтрации
    test_results = TestResult.objects.all().order_by('-completed_at')

    # Фильтрация по ФИО стажера или по названию теста
    if search_query:
        test_results = test_results.filter(Q(user__full_name__icontains=search_query) | Q(user__username__icontains=search_query))

    if test_query:
        test_results = test_results.filter(test__title__icontains=test_query)

    # Фильтрация по дате
    if start_date:
        test_results = test_results.filter(completed_at__gte=parse_date(start_date))
    if end_date:
        test_results = test_results.filter(completed_at__lte=parse_date(end_date))

    # Пагинация результатов
    paginator = Paginator(test_results, 10)  # 10 результатов на страницу
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'test_reports.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'test_query': test_query,
        'start_date': start_date,
        'end_date': end_date,
    })


@staff_member_required
def completed_internships_report(request):
    # Получаем параметры фильтрации
    search_query = request.GET.get('search', '')
    position_query = request.GET.get('position', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    # Основной запрос для выборки завершенных стажировок
    internships = Internship.objects.all()

    # Фильтрация по ФИО стажера
    if search_query:
        internships = internships.filter(
            Q(intern__full_name__icontains=search_query) |
            Q(intern__username__icontains=search_query)
        )

    # Фильтрация по позиции
    if position_query:
        internships = internships.filter(position__name__icontains=position_query)

    # Фильтрация по дате начала и завершения стажировки
    if start_date:
        internships = internships.filter(start_date__gte=parse_date(start_date))
    if end_date:
        internships = internships.filter(start_date__lte=parse_date(end_date))

    # Фильтруем только завершенные стажировки
    completed_internships = []
    for internship in internships:
        completed_stages = StageProgress.objects.filter(intern=internship.intern, completed=True)
        all_tests = TestResult.objects.filter(user=internship.intern)
        if completed_stages.exists() and all_tests.exists():
            internship.completed_at = completed_stages.order_by('-completion_date').first().completion_date
            internship.test_results = all_tests  # Добавляем результаты тестов
            completed_internships.append(internship)

    # Пагинация на 10 записей на страницу
    paginator = Paginator(completed_internships, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'completed_internships_report.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'position_query': position_query,
        'start_date': start_date,
        'end_date': end_date,
    })


@staff_member_required
def mentor_report(request):
    department_query = request.GET.get('department', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    mentors = CustomUser.objects.filter(role='mentor')

    if department_query:
        mentors = mentors.filter(department__name__icontains=department_query)

    if start_date and end_date:
        mentors = mentors.filter(intern_internships__start_date__range=[start_date, end_date])

    mentor_stats = []

    for mentor in mentors:
        # Количество стажеров под руководством ментора
        internships = Internship.objects.filter(mentor=mentor)
        total_interns = internships.count()

        # Количество завершенных стажировок
        completed_internships = internships.filter(intern__stage_progresses__completed=True).distinct().count()

        # Количество стажировок в процессе
        in_progress_internships = total_interns - completed_internships

        # Среднее время подтверждения материалов
        avg_confirmation_time = MaterialProgress.objects.filter(
            intern__in=internships.values_list('intern', flat=True),
            status='completed'
        ).aggregate(avg_time=Avg(F('confirmation_date') - F('completion_date')))

        # Процент успешности по тестам (используем related_name 'test_results' в модели TestResult)
        total_tests = TestResult.objects.filter(user__in=internships.values_list('intern', flat=True)).count()
        successful_tests = TestResult.objects.filter(user__in=internships.values_list('intern', flat=True), score__gte=60).count()  # Считаем сданные тесты

        if total_tests > 0:
            test_success_rate = (successful_tests / total_tests) * 100
        else:
            test_success_rate = 0

        mentor_stats.append({
            'mentor': mentor,
            'total_interns': total_interns,
            'completed_internships': completed_internships,
            'in_progress_internships': in_progress_internships,
            'test_success_rate': test_success_rate,
            'avg_confirmation_time': avg_confirmation_time['avg_time'] or timedelta(0),
        })

    return render(request, 'mentor_report.html', {
        'mentor_stats': mentor_stats,
        'department_query': department_query,
        'start_date': start_date,
        'end_date': end_date,
    })


@staff_member_required
def department_materials_report(request):
    # Фильтрация по департаменту
    department_query = request.GET.get('department', '')

    departments = Department.objects.all()

    if department_query:
        departments = departments.filter(name__icontains=department_query)

    department_stats = []

    for department in departments:
        # Позиции в этом департаменте
        positions = Position.objects.filter(department=department)

        position_data = []

        for position in positions:
            # Количество материалов для каждой позиции
            materials_count = Material.objects.filter(position=position).count()

            # Количество тестов для каждой позиции
            tests_count = Test.objects.filter(position=position).count()

            # Количество материалов для каждого этапа
            stages = Material.objects.filter(position=position).values('stage').annotate(
                materials_per_stage=Count('id'))

            # Формируем данные для каждой позиции
            position_data.append({
                'position': position,
                'materials_count': materials_count,
                'tests_count': tests_count,
                'stages': stages,
            })

        department_stats.append({
            'department': department,
            'positions': position_data,
        })

    return render(request, 'department_materials_report.html', {
        'department_stats': department_stats,
        'department_query': department_query,
    })