from collections import defaultdict
from tests.models import TestResult


def test_quality_stats(interns):
    test_data = defaultdict(list)

    results = TestResult.objects.filter(user__in=interns)

    for r in results:
        accuracy = (r.correct_answers_count / r.total_questions_count) * 100
        test_data[r.test.title].append({
            "accuracy": accuracy,
            "errors": r.total_questions_count - r.correct_answers_count
        })

    summary = []
    for test, values in test_data.items():
        avg_accuracy = sum(v["accuracy"] for v in values) / len(values)
        avg_errors = sum(v["errors"] for v in values) / len(values)

        summary.append({
            "test": test,
            "avg_accuracy": round(avg_accuracy, 2),
            "avg_errors": round(avg_errors, 2),
        })

    summary.sort(key=lambda x: x["avg_accuracy"])

    return {
        "hardest_tests": summary[:3],
        "easiest_tests": summary[-3:],
        "all_tests": summary
    }
