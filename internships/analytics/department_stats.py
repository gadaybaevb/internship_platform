from collections import defaultdict
from tests.models import TestResult
from internships.models import Internship


def department_analytics(interns):
    dep_data = defaultdict(list)

    for intern in interns:
        internship = Internship.objects.filter(intern=intern).select_related('position__department').first()
        if not internship or not internship.position or not internship.position.department:
            continue

        results = TestResult.objects.filter(user=intern)

        for r in results:
            accuracy = (r.correct_answers_count / r.total_questions_count) * 100
            dep_data[internship.position.department.name].append(accuracy)

    summary = []
    for dep, values in dep_data.items():
        summary.append({
            "department": dep,
            "avg_accuracy": round(sum(values) / len(values), 2),
            "tests_count": len(values)
        })

    return summary
