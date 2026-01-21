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
        # 1. Берем все стажировки, которые начались до конца выбранного месяца
        all_internships = Internship.objects.select_related(
            'intern', 'mentor', 'position'
        ).filter(start_date__lte=month_end)

        admin_intern_stats = []

        for internship in all_internships:
            # Рассчитываем дату окончания стажировки по плану
            end_date = internship.start_date + timedelta(
                days=internship.position.duration_days
            )

            # ЧТОБЫ ШОИРА НЕ ПРОПАДАЛА В ЯНВАРЕ:
            # Убираем жесткое условие "end_date >= month_start", если хотим видеть её всегда.
            # Оставляем только проверку на начало.
            if internship.start_date <= month_end:

                # --- ЛОГИКА ПОДСЧЕТА МАТЕРИАЛОВ С ФИЛЬТРОМ ПО ДАТЕ ---
                total_m = Material.objects.filter(
                    position=internship.position
                ).count()

                # Считаем только то, что было подтверждено до КОНЦА выбранного месяца
                completed_m_query = MaterialProgress.objects.filter(
                    intern=internship.intern,
                    material__position=internship.position,
                    status='completed',
                    confirmation_date__date__lte=month_end
                )
                completed_m = completed_m_query.count()

                # --- БЛОК ДИАГНОСТИКИ (ПРИНТЫ) ---
                if "Шоира" in internship.intern.full_name:
                    print(f"\n--- ОТЧЕТ ДЛЯ {internship.intern.full_name} ---")
                    print(f"Период фильтра (месяц): {month_start} - {month_end}")
                    print(f"Срок стажировки по плану: {internship.start_date} - {end_date}")
                    print(f"Подтверждено материалов до {month_end}: {completed_m}")
                # --- КОНЕЦ ПРИНТОВ ---

                percent = round((completed_m / total_m) * 100, 2) if total_m else 0

                # --- ИСПРАВЛЕННЫЙ СТАТУС (БЕЗ ОШИБКИ completion_date) ---
                # Проверяем, завершены ли ВСЕ материалы на текущий момент
                is_full_done = internship.is_completed()

                # Ищем дату последнего подтвержденного материала
                last_progress = MaterialProgress.objects.filter(
                    intern=internship.intern,
                    material__position=internship.position,
                    status='completed'
                ).order_by('-confirmation_date').first()

                last_conf_date = last_progress.confirmation_date.date() if last_progress and last_progress.confirmation_date else None

                # Логика определения статуса
                if is_full_done and last_conf_date and last_conf_date <= month_end:
                    status = 'Завершена'
                elif today > end_date:
                    status = 'Срок истёк'
                else:
                    status = 'Активна'

                admin_intern_stats.append({
                    'intern': internship.intern,
                    'mentor': internship.mentor,
                    'position': internship.position,
                    'completed': completed_m,
                    'total': total_m,
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