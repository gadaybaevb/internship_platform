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




@login_required
def home(request):
    user = request.user
    today = now().date()

    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))

    month_start = date(selected_year, selected_month, 1)
    month_end = date(
        selected_year,
        selected_month,
        monthrange(selected_year, selected_month)[1]
    )

    months = [
        (1, 'Январь'), (2, 'Февраль'), (3, 'Март'), (4, 'Апрель'),
        (5, 'Май'), (6, 'Июнь'), (7, 'Июль'), (8, 'Август'),
        (9, 'Сентябрь'), (10, 'Октябрь'), (11, 'Ноябрь'), (12, 'Декабрь'),
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

        all_internships = Internship.objects.select_related(
            'intern', 'mentor', 'position'
        )

        internships = []

        for internship in all_internships:
            end_date = internship.start_date + timedelta(
                days=internship.position.duration_days
            )

            if internship.start_date <= month_end and end_date >= month_start:
                internships.append(internship)

        # ===== СТАТИСТИКА =====
        interns_this_month = Internship.objects.filter(
            start_date__month=selected_month,
            start_date__year=selected_year
        ).count()

        mentors_this_month = Internship.objects.filter(
            start_date__month=selected_month,
            start_date__year=selected_year
        ).exclude(mentor=None).values('mentor').distinct().count()

        total_interns = Internship.objects.count()
        total_mentors = Internship.objects.exclude(
            mentor=None
        ).values('mentor').distinct().count()

        # ===== ПРОГРЕСС ЗА ПЕРИОД =====
        total_materials = 0
        completed_materials = 0

        for internship in internships:
            total_materials += Material.objects.filter(
                position=internship.position
            ).count()

            completed_materials += MaterialProgress.objects.filter(
                intern=internship.intern,
                material__position=internship.position,
                mentor_confirmed=True,
                confirmation_date__date__range=(month_start, month_end)
            ).count()

        total_completion_percent = round(
            (completed_materials / total_materials) * 100, 2
        ) if total_materials else 0

        # ===== ТАБЛИЦА =====
        admin_intern_stats = []

        for internship in internships:
            intern = internship.intern

            total_m = Material.objects.filter(
                position=internship.position
            ).count()

            completed_m = MaterialProgress.objects.filter(
                intern=intern,
                material__position=internship.position,
                mentor_confirmed=True,
                confirmation_date__date__range=(month_start, month_end)
            ).count()

            percent = round((completed_m / total_m) * 100, 2) if total_m else 0

            if internship.is_completed():
                status = 'Завершена'
            elif internship.internship_duration_expired():
                status = 'Срок истёк'
            else:
                status = 'Активна'

            admin_intern_stats.append({
                'intern': intern,
                'mentor': internship.mentor,
                'position': internship.position,
                'completed': completed_m,
                'total': total_m,
                'percent': percent,
                'status': status,
            })

        context.update({
            'interns_this_month': interns_this_month,
            'mentors_this_month': mentors_this_month,
            'total_interns': total_interns,
            'total_mentors': total_mentors,
            'total_completion_percent': total_completion_percent,
            'admin_intern_stats': admin_intern_stats,
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