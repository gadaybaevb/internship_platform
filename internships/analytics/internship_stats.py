from internships.models import Internship, MaterialProgress
from tests.models import TestResult


def internship_duration_stats(interns):
    durations = []

    for intern in interns:
        internship = Internship.objects.filter(intern=intern).first()
        if not internship:
            continue

        last_material = (
            MaterialProgress.objects
            .filter(intern=intern, completion_date__isnull=False)
            .order_by('-completion_date')
            .first()
        )

        last_test = (
            TestResult.objects
            .filter(user=intern)
            .order_by('-completed_at')
            .first()
        )

        last_date = None
        if last_material and last_test:
            last_date = max(last_material.completion_date.date(), last_test.completed_at.date())
        elif last_material:
            last_date = last_material.completion_date.date()
        elif last_test:
            last_date = last_test.completed_at.date()

        if last_date:
            durations.append((last_date - internship.start_date).days)

    if not durations:
        return {}

    durations.sort()
    count = len(durations)

    return {
        "avg_internship_days": round(sum(durations) / count, 2),
        "median_internship_days": durations[count // 2],
        "min_internship_days": min(durations),
        "max_internship_days": max(durations),
    }
