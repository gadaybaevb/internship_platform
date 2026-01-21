from django.shortcuts import render, redirect, get_object_or_404
from .forms import CustomUserCreationForm, CustomUserEditForm
from .models import CustomUser
import random
import string
from django.core.paginator import Paginator
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.urls import reverse_lazy
from internships.models import Internship, MaterialProgress, StageProgress, Material
from django.utils.timezone import now
from datetime import timedelta, date
from django.utils.timezone import now
from datetime import timedelta, date
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import F, ExpressionWrapper, DateField
from calendar import monthrange
from django.db.models import Count, Q


@login_required
def home(request):
    user = request.user

    if not user.is_authenticated:
        return redirect('login')

    today = now().date()

    # ===== МЕСЯЦ / ГОД (по умолчанию текущие) =====
    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    month_start = date(selected_year, selected_month, 1)
    month_end = date(
        selected_year,
        selected_month,
        monthrange(selected_year, selected_month)[1]
    )

    months = [
        (1, 'Январь'),
        (2, 'Февраль'),
        (3, 'Март'),
        (4, 'Апрель'),
        (5, 'Май'),
        (6, 'Июнь'),
        (7, 'Июль'),
        (8, 'Август'),
        (9, 'Сентябрь'),
        (10, 'Октябрь'),
        (11, 'Ноябрь'),
        (12, 'Декабрь'),
    ]

    years = list(range(2023, today.year + 2))

    context = {
        'months': months,
        'years': years,
        'selected_month': selected_month,
        'selected_year': selected_year,
    }

    # ===================== ADMIN =====================
    if user.role == 'admin':
        # 1. Фильтруем стажировки, которые пересекаются с выбранным месяцем
        # Стажировка активна, если она началась до конца месяца И (не имеет даты окончания или закончилась после начала месяца)
        internships_queryset = Internship.objects.filter(
            start_date__lte=month_end
        ).select_related('intern', 'mentor', 'position')

        # 2. Используем annotate для подсчета материалов прямо в БД
        # Это заменит цикл и десятки запросов на 1 эффективный запрос
        admin_intern_stats_query = internships_queryset.annotate(
            completed_count=Count(
                'intern__materialprogress',
                filter=Q(
                    'intern__materialprogress__material__position' == F('position'),  # материалы именно этой позиции
                    intern__materialprogress__status='completed',
                    intern__materialprogress__confirmation_date__date__lte=month_end
                )
            ),
            total_count=Count(
                'position__material'  # Общее кол-во материалов для этой позиции
            )
        )

        admin_intern_stats = []

        for item in admin_intern_stats_query:
            # Рассчитываем окончание стажировки
            end_date_calc = item.start_date + timedelta(days=item.position.duration_days)

            # Пропускаем те, что закончились до начала выбранного месяца
            if end_date_calc < month_start:
                continue

            percent = round((item.completed_count / item.total_count) * 100, 2) if item.total_count else 0

            # Определяем статус
            if item.is_completed() and item.confirmation_date and item.confirmation_date.date() <= month_end:
                status = 'Завершена'
            elif month_end > end_date_calc:
                status = 'Срок истёк'
            else:
                status = 'Активна'

            admin_intern_stats.append({
                'intern': item.intern,
                'mentor': item.mentor,
                'position': item.position,
                'completed': item.completed_count,
                'total': item.total_count,
                'percent': percent,
                'status': status,
            })


    # ===================== MENTOR =====================
    elif user.role == 'mentor':
        internships = (
            Internship.objects
            .filter(mentor=user)
            .select_related('intern', 'position')
        )

        interns_this_month = internships.filter(
            start_date__month=today.month,
            start_date__year=today.year
        ).count()

        total_interns = internships.count()

        intern_stats = []
        best_intern = None
        best_percent = 0
        avg_sum = 0

        for internship in internships:
            intern = internship.intern

            total_m = Material.objects.filter(
                position=internship.position
            ).count()

            completed_m = MaterialProgress.objects.filter(
                intern=intern,
                material__position=internship.position,
                status='completed'
            ).count()

            percent = round((completed_m / total_m) * 100, 2) if total_m else 0
            avg_sum += percent

            if internship.is_completed():
                status = 'Завершена'
            elif internship.internship_duration_expired():
                status = 'Срок истёк'
            else:
                status = 'Активна'

            intern_stats.append({
                'intern': intern,
                'completed': completed_m,
                'total': total_m,
                'percent': percent,
                'status': status,
            })

            if percent > best_percent:
                best_percent = percent
                best_intern = intern

        context.update({
            'interns_this_month': interns_this_month,
            'total_interns': total_interns,
            'avg_completion_percent': round(avg_sum / total_interns, 2) if total_interns else 0,
            'intern_stats': intern_stats,
            'best_intern': best_intern,
            'best_intern_percent': best_percent,
        })

    # ===================== INTERN =====================
    elif user.role == 'intern':
        internship = Internship.objects.filter(intern=user).select_related('position').first()

        if internship:
            materials = MaterialProgress.objects.filter(
                intern=user,
                material__position=internship.position
            )

            completed = materials.filter(status='completed').count()
            total = materials.count()

            end_date = internship.start_date + timedelta(
                days=internship.position.duration_days
            )

            days_left = (end_date - today).days

            context.update({
                'completed_materials': completed,
                'total_materials': total,
                'days_left': days_left,
                'internship': internship,
            })

    return render(request, 'home.html', context)


@staff_member_required
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})


@staff_member_required
def user_list(request):
    users = CustomUser.objects.all().order_by('id')
    paginator = Paginator(users, 50)  # Пагинация по 50 записей
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user_list.html', {'page_obj': page_obj})


@staff_member_required
def user_edit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        # Проверяем, нажата ли кнопка "Сбросить пароль"
        if 'reset_password' in request.POST:
            print("Кнопка 'Сбросить пароль' нажата")  # Отладочное сообщение

            # Генерация случайного пароля
            new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            print("Новый пароль:", new_password)  # Отладочное сообщение

            # Устанавливаем новый пароль
            user.set_password(new_password)
            user.save()
            messages.success(request, f'Пароль успешно сброшен. Новый пароль: {new_password}')
            print("Сообщение о сбросе пароля добавлено")  # Отладочное сообщение

            # Перенаправление обратно на страницу редактирования пользователя
            return redirect('user_edit', user_id=user_id)

        # Обрабатываем изменения данных пользователя
        form = CustomUserEditForm(request.POST, instance=user)
        if form.is_valid():
            print("Форма редактирования данных валидна")  # Отладочное сообщение
            form.save()
            messages.success(request, 'Данные пользователя успешно обновлены.')
            return redirect('user_list')
        else:
            print("Форма редактирования данных не валидна")  # Отладочное сообщение
    else:
        form = CustomUserEditForm(instance=user)
        print("GET-запрос: отображение формы редактирования")  # Отладочное сообщение

    return render(request, 'user_edit.html', {'form': form, 'user': user})


@staff_member_required
def user_delete(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        user.delete()
        return redirect('user_list')

    return render(request, 'user_confirm_delete.html', {'user': user})


class CustomLoginView(LoginView):
    template_name = 'login.html'  # Путь к шаблону логина
    redirect_authenticated_user = True  # Перенаправлять, если пользователь уже аутентифицирован
    next_page = reverse_lazy('home')  # Перенаправление после успешного входа


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')  # Перенаправление на страницу логина после выхода