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
from django.db.models import Q


@login_required
def home(request):
    user = request.user
    context = {}

    if not user.is_authenticated:
        return redirect('login')

    if user.role == 'admin':
        today = now()
        current_month = today.month
        current_year = today.year

        # ===== СТАЖЁРЫ И МЕНТОРЫ =====
        interns_this_month = Internship.objects.filter(
            start_date__month=current_month,
            start_date__year=current_year
        ).count()

        mentors_this_month = Internship.objects.filter(
            start_date__month=current_month,
            start_date__year=current_year
        ).exclude(mentor=None).values('mentor').distinct().count()

        total_interns = Internship.objects.count()
        total_mentors = Internship.objects.exclude(mentor=None).values('mentor').distinct().count()

        # ===== МАТЕРИАЛЫ =====
        total_materials_progress = MaterialProgress.objects.count()
        completed_materials_total = MaterialProgress.objects.filter(status='completed').count()

        total_completion_percent = (
            round((completed_materials_total / total_materials_progress) * 100, 2)
            if total_materials_progress else 0
        )

        # ===== АКТИВНЫЕ СТАЖЁРЫ =====
        active_interns = Internship.objects.select_related('intern', 'position')

        active_stats = []
        intern_of_month = None
        best_percent = 0

        for internship in active_interns:
            intern = internship.intern

            total_materials = Material.objects.filter(
                position=internship.position
            ).count()

            completed_materials = MaterialProgress.objects.filter(
                intern=intern,
                status='completed'
            ).count()

            percent = round((completed_materials / total_materials) * 100, 2) if total_materials else 0

            active_stats.append({
                'intern': intern,
                'completed': completed_materials,
                'total': total_materials,
                'percent': percent,
            })

            # Стажёр месяца
            if percent > best_percent:
                best_percent = percent
                intern_of_month = intern

        context.update({
            # Месяц
            'interns_this_month': interns_this_month,
            'mentors_this_month': mentors_this_month,

            # Всего
            'total_interns': total_interns,
            'total_mentors': total_mentors,

            # Материалы
            'total_completion_percent': total_completion_percent,
            'active_stats': active_stats,

            # ТОП
            'intern_of_month': intern_of_month,
            'intern_of_month_percent': best_percent,
        })



    elif user.role == 'mentor':
        today = now()
        current_month = today.month
        current_year = today.year
        internships = Internship.objects.filter(
            mentor=user
        ).select_related('intern', 'position')
        # ===== СТАЖЁРЫ =====
        interns_this_month = internships.filter(
            start_date__month=current_month,
            start_date__year=current_year
        ).count()
        total_interns = internships.count()
        intern_stats = []
        best_intern = None
        best_percent = 0
        avg_percent_sum = 0

        for internship in internships:
            intern = internship.intern
            total_materials = Material.objects.filter(
                position=internship.position
            ).count()
            completed_materials = MaterialProgress.objects.filter(
                intern=intern,
                status='completed'
            ).count()
            percent = round((completed_materials / total_materials) * 100, 2) if total_materials else 0
            avg_percent_sum += percent
            # Статус стажировки
            if internship.is_completed():
                status = 'Завершена'
            elif internship.internship_duration_expired():
                status = 'Срок истёк'
            else:
                status = 'Активна'
            intern_stats.append({
                'intern': intern,
                'completed': completed_materials,
                'total': total_materials,
                'percent': percent,
                'status': status,
            })
            # Лучший стажёр
            if percent > best_percent:
                best_percent = percent
                best_intern = intern
        avg_completion_percent = round(
            avg_percent_sum / total_interns, 2
        ) if total_interns else 0
        context.update({
            # Месяц
            'interns_this_month': interns_this_month,
            # Всего
            'total_interns': total_interns,
            'avg_completion_percent': avg_completion_percent,
            # Таблица
            'intern_stats': intern_stats,
            # ТОП
            'best_intern': best_intern,
            'best_intern_percent': best_percent,
        })

    elif user.role == 'intern':
        # Контент для стажера
        internship = Internship.objects.filter(intern=user).first()

        if internship:
            materials = MaterialProgress.objects.filter(intern=user)
            completed_materials = materials.filter(status='completed').count()
            total_materials = materials.count()

            # Оставшиеся дни до окончания стажировки
            end_date = internship.start_date + timedelta(days=internship.position.duration_days)

            # Преобразуем `now()` в `date`, чтобы обе переменные были одного типа
            days_left = (end_date - now().date()).days

            context.update({
                'completed_materials': completed_materials,
                'total_materials': total_materials,
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