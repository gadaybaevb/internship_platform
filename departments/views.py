from django.shortcuts import render, get_object_or_404, redirect
from .models import Department, Position
from .forms import DepartmentForm, PositionForm
from django.core.paginator import Paginator


def department_list(request):
    departments = Department.objects.all()
    paginator = Paginator(departments, 50)  # Пагинация по 50 записей
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'department_list.html', {'page_obj': page_obj})


def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('department_list')
    else:
        form = DepartmentForm()
    return render(request, 'department_form.html', {'form': form})


def department_edit(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            return redirect('department_list')
    else:
        form = DepartmentForm(instance=department)

    return render(request, 'department_form.html', {'form': form, 'department': department})


def department_delete(request, department_id):
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        department.delete()
        return redirect('department_list')

    return render(request, 'department_confirm_delete.html', {'department': department})


def position_create(request):
    if request.method == 'POST':
        form = PositionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('position_list')  # Исправляем редирект на список позиций
    else:
        form = PositionForm()

    return render(request, 'position_form.html', {'form': form, 'position': None})


def position_list(request):
    positions = Position.objects.all()
    paginator = Paginator(positions, 50)  # Пагинация по 50 записей
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'position_list.html', {'page_obj': page_obj})


def position_edit(request, position_id):
    position = get_object_or_404(Position, id=position_id)

    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            return redirect('position_list')
    else:
        form = PositionForm(instance=position)

    return render(request, 'position_form.html', {'form': form, 'position': position})


def position_delete(request, position_id):
    position = get_object_or_404(Position, id=position_id)

    if request.method == 'POST':
        position.delete()
        return redirect('position_list')

    return render(request, 'position_confirm_delete.html', {'position': position})