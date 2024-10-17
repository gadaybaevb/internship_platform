from .models import StageProgress


def create_stage_progress(internship):
    # Создаем этапы для позиции, на которую назначен стажёр
    for stage_number in range(1, internship.position.stages_count + 1):
        StageProgress.objects.create(
            intern=internship.intern,
            position=internship.position,
            stage=stage_number,
            completed=False
        )