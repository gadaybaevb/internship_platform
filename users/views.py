from django.shortcuts import render, redirect, get_object_or_404
from .forms import CustomUserCreationForm, CustomUserEditForm
from .models import CustomUser
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


def home(request):
    user = request.user
    context = {}

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


def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = CustomUserCreationForm()

    return render(request, 'register.html', {'form': form})


def user_list(request):
    users = CustomUser.objects.all().order_by('id')
    paginator = Paginator(users, 50)  # Пагинация по 50 записей
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'user_list.html', {'page_obj': page_obj})


def user_edit(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)

    if request.method == 'POST':
        form = CustomUserEditForm(request.POST, instance=user)
        password_form = SetPasswordForm(user, request.POST)  # Используем SetPasswordForm

        if form.is_valid() and password_form.is_valid():
            form.save()
            password_form.save()
            messages.success(request, 'Данные пользователя и пароль успешно обновлены.')
            return redirect('user_list')
    else:
        form = CustomUserEditForm(instance=user)
        password_form = SetPasswordForm(user)  # Используем SetPasswordForm

    return render(request, 'user_edit.html', {'form': form, 'password_form': password_form, 'user': user})


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