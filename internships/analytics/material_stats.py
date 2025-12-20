from datetime import timedelta
from django.db.models import Min
from internships.models import MaterialProgress, Internship


def material_time_stats(interns):
    """
    Среднее / медианное время прохождения одного материала
    """
    durations = []

    for intern in interns:
        internship = Internship.objects.filter(intern=intern).first()
        if not internship:
            continue

        materials = (
            MaterialProgress.objects
            .filter(intern=intern, completed=True, completion_date__isnull=False)
            .order_by('completion_date')
        )

        prev_date = None
        for mp in materials:
            if prev_date:
                durations.append((mp.completion_date - prev_date).days)
            else:
                durations.append((mp.completion_date.date() - internship.start_date).days)
            prev_date = mp.completion_date

    if not durations:
        return {}

    durations.sort()
    count = len(durations)

    return {
        "avg_material_days": round(sum(durations) / count, 2),
        "median_material_days": durations[count // 2],
        "min_material_days": min(durations),
        "max_material_days": max(durations),
    }
