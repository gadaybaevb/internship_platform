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
from internships.models import Internship, MaterialProgress, StageProgress
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
    # Ищем все материалы со статусом 'pending'
    materials_with_pending_status = MaterialProgress.objects.filter(status='pending')

    print(f"Found {materials_with_pending_status.count()} materials with 'pending' status.")

    # Обрабатываем эти материалы
    for progress in materials_with_pending_status:
        # Проверяем, если у материала нет отзыва
        if not progress.feedback:
            print(f"Progress ID: {progress.id} has no feedback. Changing status to 'not_started'.")
            progress.status = 'not_started'  # Сбрасываем статус на 'не пройден'
            progress.save()  # Сохраняем изменения
        else:
            print(f"Progress ID: {progress.id} has feedback.")



    if not user.is_authenticated:
        return redirect('login')

    if user.role == 'admin':
        # Администраторский контент
        current_month = now().month
        current_year = now().year

        interns_this_month = Internship.objects.filter(start_date__month=current_month, start_date__year=current_year).count()
        mentors_this_month = Internship.objects.filter(start_date__month=current_month, start_date__year=current_year).values('mentor').distinct().count()

        total_interns = Internship.objects.count()
        total_mentors = Internship.objects.values('mentor').distinct().count()

        context.update({
            'interns_this_month': interns_this_month,
            'mentors_this_month': mentors_this_month,
            'total_interns': total_interns,
            'total_mentors': total_mentors,
        })

    elif user.role == 'mentor':
        # Контент для ментора
        current_month = now().month
        current_year = now().year

        interns_this_month = Internship.objects.filter(mentor=user, start_date__month=current_month, start_date__year=current_year)
        total_interns = Internship.objects.filter(mentor=user)

        context.update({
            'interns_this_month': interns_this_month,
            'total_interns': total_interns,
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