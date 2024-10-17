from django.shortcuts import render, get_object_or_404, redirect
from .models import Material, Position, Internship, StageProgress, MaterialProgress
from departments.models import Department
from django.contrib.auth import get_user_model
from .forms import MaterialForm
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib import messages
from users.models import CustomUser
from .utils import create_stage_progress
from datetime import timedelta, datetime
from django.utils import timezone
from notifications.models import Notification
from tests.models import Test


User = get_user_model()


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

    return render(request, 'material_form.html', {'form': form})


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


def material_delete(request, material_id):
    material = get_object_or_404(Material, id=material_id)

    if request.method == 'POST':
        material.delete()
        return redirect('material_list')

    return render(request, 'material_confirm_delete.html', {'material': material})


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
        Notification.objects.create(user=internship.intern.username, message=message)

        return redirect('internship_list')

    mentors = CustomUser.objects.filter(role='mentor')
    positions = Position.objects.all()  # Получаем все доступные позиции

    context = {
        'internship': internship,
        'mentors': mentors,
        'positions': positions,  # Передаем позиции в шаблон
    }
    return render(request, 'assign_mentor.html', context)


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


def dashboard(request):
    user = request.user
    check_deadlines(user)  # Проверяем дедлайны

    if user.role == 'admin':
        # Администратор видит всех стажеров и их прогресс
        internships = Internship.objects.all()
    elif user.role == 'mentor':
        # Ментор видит только своих стажеров
        internships = Internship.objects.filter(mentor=user)

        for internship in internships:
            # Для каждого стажера добавляем количество материалов, ожидающих подтверждения
            pending_materials_count = MaterialProgress.objects.filter(
                intern=internship.intern,
                status='pending'
            ).count()
            internship.pending_materials_count = pending_materials_count

        # Если ментор выбирает стажера, он видит его прогресс
        intern_id = request.GET.get('intern_id')
        if intern_id:
            intern = get_object_or_404(CustomUser, id=intern_id)
            materials = MaterialProgress.objects.filter(intern=intern).order_by('material__stage')

            # Разделение материалов по статусам
            pending_materials = materials.filter(status='pending')
            completed_materials = materials.filter(status='completed')
            not_started_materials = materials.filter(status='not_started')

            # Подтверждение ментором материалов в статусе "Ожидание"
            if request.method == 'POST':
                material_id = request.POST.get('material_id')
                material_progress = get_object_or_404(MaterialProgress, id=material_id)
                material_progress.status = 'completed'
                material_progress.mentor_confirmed = True
                material_progress.confirmation_date = timezone.now()
                material_progress.save()

                # Уведомляем стажера о том, что материал был подтвержден
                Notification.objects.create(user=intern, message=f'Ментор подтвердил завершение материала: {material_progress.material.title}')

                return redirect('dashboard')

            return render(request, 'mentor_dashboard_intern_materials.html', {
                'intern': intern,
                'pending_materials': pending_materials,
                'completed_materials': completed_materials,
                'not_started_materials': not_started_materials
            })

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
    return render(request, 'mentor_admin_dashboard.html', {'page_obj': page_obj, 'role': user.role})



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


def intern_materials(request):
    intern = request.user
    check_deadlines(intern)

    if not intern.position:
        return render(request, 'intern_materials.html', {'materials': [], 'progress_summary': {}})

    internship = Internship.objects.filter(intern=intern).first()

    if not internship or not internship.start_date:
        return render(request, 'intern_materials.html', {'materials': [], 'progress_summary': {}})

    materials = Material.objects.filter(position=intern.position).order_by('stage')

    # Готовим данные о прогрессе по материалам и этапам
    material_list = []
    for material in materials:
        # Создаем запись в StageProgress, если её нет для текущего этапа
        stage_progress, created = StageProgress.objects.get_or_create(
            intern=intern,
            position=intern.position,
            stage=material.stage,
            defaults={'completed': False}
        )

        material_progress = MaterialProgress.objects.filter(intern=intern, material=material).first()

        if material_progress:
            status = material_progress.status  # Статус берем напрямую из базы
        else:
            status = 'not_started'

        material_list.append({
            'material': material,
            'status': status
        })

    total_materials = len(materials)
    completed_materials = MaterialProgress.objects.filter(intern=intern, completed=True).count()
    remaining_materials = total_materials - completed_materials

    start_date = internship.start_date
    end_date = start_date + timedelta(days=intern.position.duration_days)

    end_date_time = datetime.combine(end_date, datetime.min.time())
    end_date_time_aware = timezone.make_aware(end_date_time)
    time_left = (end_date_time_aware - timezone.now()).days if end_date_time_aware > timezone.now() else 0

    progress_summary = {
        'total': total_materials,
        'completed': completed_materials,
        'remaining': remaining_materials,
        'time_left': time_left,
    }

    # Получаем все тесты, привязанные к позиции
    tests = Test.objects.filter(position=intern.position)

    # Проверяем завершение этапов для тестов
    stage_completion = {}
    for stage in StageProgress.objects.filter(intern=intern, position=intern.position):
        stage_completion[stage.stage] = stage.completed

    return render(request, 'intern_materials.html', {
        'materials': material_list,  # Передаем список материалов и их статусы
        'progress_summary': progress_summary,
        'tests': tests,  # Передаем тесты
        'stage_completion': stage_completion,  # Передаем завершение этапов
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
